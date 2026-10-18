#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <cstring>
#include <dlfcn.h>
#include <fcntl.h>
#include <iostream>
#include <string>
#include <unistd.h>
#include <vector>

#include "ggml-backend.h"
#include "ggml-cpu.h"
#include "ggml.h"
#include "llama.h"

using compute_function = ggml_status (*)(ggml_context *, ggml_cgraph *, int);
constexpr int layer_count = 48;
constexpr std::array<off_t, layer_count> gate_base{612307456,1015903744,1419500032,1823096320,2226692608,2630288896,2981710336,3333131776,3736728064,4088149504,4439570944,4843167232,5194588672,5546010112,5949606400,6301027840,6652449280,7056045568,7407467008,7758888448,8162484736,8513906176,8865327616,9268923904,9620345344,9971766784,10375363072,10726784512,11078205952,11481802240,11833223680,12184645120,12588241408,12939662848,13291084288,13694680576,14046102016,14397523456,14801119744,15152541184,15503962624,15907558912,16311155200,16714751488,17118347776,17521944064,17925540352,18329136640};
constexpr std::array<off_t, layer_count> up_base{726610432,1130206720,1533803008,1937399296,2340995584,2744591872,3096013312,3447434752,3851031040,4202452480,4553873920,4957470208,5308891648,5660313088,6063909376,6415330816,6766752256,7170348544,7521769984,7873191424,8276787712,8628209152,8979630592,9383226880,9734648320,10086069760,10489666048,10841087488,11192508928,11596105216,11947526656,12298948096,12702544384,13053965824,13405387264,13808983552,14160404992,14511826432,14915422720,15266844160,15618265600,16021861888,16425458176,16829054464,17232650752,17636247040,18039843328,18443439616};
constexpr std::array<off_t, layer_count> down_base{447156736,850753024,1254349312,1657945600,2061541888,2465138176,2868464128,3219885568,3571577344,3974903296,4326324736,4678016512,5081342464,5432763904,5784455680,6187781632,6539203072,6890894848,7294220800,7645642240,7997334016,8400659968,8752081408,9103773184,9507099136,9858520576,10210212352,10613538304,10964959744,11316651520,11719977472,12071398912,12423090688,12826416640,13177838080,13529529856,13932855808,14284277248,14635969024,15039294976,15390716416,15742408192,16146004480,16549600768,16953197056,17356793344,17760389632,18163985920};
constexpr std::array<int, layer_count> down_types{14,14,14,14,14,14,12,12,14,12,12,14,12,12,14,12,12,14,12,12,14,12,12,14,12,12,14,12,12,14,12,12,14,12,12,14,12,12,14,12,12,14,14,14,14,14,14,14};

struct layer_capture {
    std::array<int32_t, 8> route{};
    std::array<float, 8> gates{};
    std::array<float, 2048> input{};
    std::array<float, 2048> output{};
    bool route_ok = false, gates_ok = false, input_ok = false, output_ok = false;
};
struct capture_state { std::array<layer_capture, layer_count> layers{}; };

static void get_row(ggml_tensor * tensor, void * destination, size_t bytes) {
    ggml_backend_tensor_get_2d(tensor, destination, 0, bytes, 1, tensor->nb[1], bytes);
}

static bool parse_exact(const char * name, const char * prefix, int & layer) {
    const size_t length = std::strlen(prefix);
    if (std::strncmp(name, prefix, length) != 0) return false;
    char * end = nullptr;
    const long parsed = std::strtol(name + length, &end, 10);
    if (*end != '\0' || parsed < 0 || parsed >= layer_count) return false;
    layer = static_cast<int>(parsed);
    return true;
}

static bool capture_all(ggml_tensor * tensor, bool ask, void * opaque) {
    const char * name = ggml_get_name(tensor);
    int layer = -1;
    enum class kind { none, topk, weights, gate, output } selected = kind::none;
    if (parse_exact(name, "ffn_moe_topk-", layer)) selected = kind::topk;
    else if (parse_exact(name, "ffn_moe_weights_norm-", layer)) selected = kind::weights;
    else if (parse_exact(name, "ffn_moe_gate-", layer)) selected = kind::gate;
    else if (parse_exact(name, "ffn_moe_out-", layer)) selected = kind::output;
    if (selected == kind::none) return false;
    if (ask) return true;
    auto & target = static_cast<capture_state *>(opaque)->layers[layer];
    if (selected == kind::topk) {
        get_row(tensor, target.route.data(), 8 * sizeof(int32_t));
        target.route_ok = true;
    } else if (selected == kind::weights) {
        get_row(tensor, target.gates.data(), 8 * sizeof(float));
        target.gates_ok = true;
    } else if (selected == kind::gate) {
        for (ggml_tensor * source : tensor->src) {
            if (source != nullptr && source->type == GGML_TYPE_F32 && source->ne[0] == 2048) {
                get_row(source, target.input.data(), 2048 * sizeof(float));
                target.input_ok = true;
                break;
            }
        }
    } else {
        get_row(tensor, target.output.data(), 2048 * sizeof(float));
        target.output_ok = true;
    }
    return true;
}

static bool read_exact(int fd, void * output, size_t bytes, off_t offset) {
    auto * destination = static_cast<char *>(output);
    size_t complete = 0;
    while (complete < bytes) {
        const ssize_t count = pread(fd, destination + complete, bytes - complete,
                                    offset + static_cast<off_t>(complete));
        if (count <= 0) return false;
        complete += static_cast<size_t>(count);
    }
    return true;
}

int main(int argc, char ** argv) {
    if (argc != 2) return 2;
    capture_state captured;
    llama_backend_init();
    llama_model_params mp = llama_model_default_params();
    mp.n_gpu_layers = 0; mp.load_mode = LLAMA_LOAD_MODE_MMAP;
    mp.lazy_mode = LLAMA_LAZY_MODE_AUTO; mp.use_extra_bufts = false;
    llama_model * model = llama_model_load_from_file(argv[1], mp);
    if (model == nullptr) return 3;
    llama_context_params cp = llama_context_default_params();
    cp.n_ctx = 16; cp.n_batch = 16; cp.n_ubatch = 16;
    cp.n_threads = 8; cp.n_threads_batch = 8;
    cp.offload_kqv = false; cp.op_offload = false;
    cp.cb_eval = capture_all; cp.cb_eval_user_data = &captured;
    llama_context * context = llama_init_from_model(model, cp);
    if (context == nullptr) return 4;
    const std::string prompt = "Hello";
    const llama_vocab * vocab = llama_model_get_vocab(model);
    int32_t count = llama_tokenize(vocab, prompt.c_str(), prompt.size(), nullptr, 0, true, true);
    if (count >= 0) return 5;
    std::vector<llama_token> tokens(static_cast<size_t>(-count));
    count = llama_tokenize(vocab, prompt.c_str(), prompt.size(), tokens.data(), tokens.size(), true, true);
    const int decode_result = llama_decode(context, llama_batch_get_one(tokens.data(), count));
    llama_free(context); llama_model_free(model); llama_backend_free();
    if (decode_result != 0) return 6;
    for (const auto & layer : captured.layers) {
        if (!layer.route_ok || !layer.gates_ok || !layer.input_ok || !layer.output_ok) return 7;
    }

    const int fd = open(argv[1], O_RDONLY);
    if (fd < 0) return 8;
    void * plugin = dlopen("/opt/homebrew/Cellar/ggml/0.23.0/libexec/libggml-cpu-apple_m2_m3.so", RTLD_NOW | RTLD_LOCAL);
    if (plugin == nullptr) return 9;
    auto compute = reinterpret_cast<compute_function>(dlsym(plugin, "ggml_graph_compute_with_ctx"));
    if (compute == nullptr) return 10;
    std::vector<char> memory(256 * 1024 * 1024);
    double global_max = 0.0, global_mean_sum = 0.0, global_error = 0.0, global_reference = 0.0;
    std::cout << "{\"schema\":\"aion.qwen3moe.packed-all-layers-exact.v1\",\"layers\":[";
    for (int layer = 0; layer < layer_count; ++layer) {
        ggml_context * direct = ggml_init({memory.size(), memory.data(), false});
        ggml_tensor * input = ggml_new_tensor_2d(direct, GGML_TYPE_F32, 2048, 1);
        std::copy(captured.layers[layer].input.begin(), captured.layers[layer].input.end(), static_cast<float *>(input->data));
        ggml_tensor * sum = nullptr;
        const ggml_type down_type = static_cast<ggml_type>(down_types[layer]);
        const off_t down_stride = down_type == GGML_TYPE_Q6_K ? 1290240 : 884736;
        for (int position = 0; position < 8; ++position) {
            const int expert = captured.layers[layer].route[position];
            ggml_tensor * gate = ggml_new_tensor_2d(direct, GGML_TYPE_Q4_K, 2048, 768);
            ggml_tensor * up = ggml_new_tensor_2d(direct, GGML_TYPE_Q4_K, 2048, 768);
            ggml_tensor * down = ggml_new_tensor_2d(direct, down_type, 768, 2048);
            if (!read_exact(fd, gate->data, ggml_nbytes(gate), gate_base[layer] + expert * 884736) ||
                !read_exact(fd, up->data, ggml_nbytes(up), up_base[layer] + expert * 884736) ||
                !read_exact(fd, down->data, ggml_nbytes(down), down_base[layer] + expert * down_stride)) return 11;
            ggml_tensor * hidden = ggml_mul(direct,
                ggml_silu(direct, ggml_mul_mat(direct, gate, input)),
                ggml_mul_mat(direct, up, input));
            ggml_tensor * output = ggml_scale(direct, ggml_mul_mat(direct, down, hidden), captured.layers[layer].gates[position]);
            sum = sum == nullptr ? output : ggml_add(direct, sum, output);
        }
        ggml_cgraph * graph = ggml_new_graph_custom(direct, GGML_DEFAULT_GRAPH_SIZE, false);
        ggml_build_forward_expand(graph, sum);
        if (compute(direct, graph, 8) != GGML_STATUS_SUCCESS) return 12;
        const auto * actual = static_cast<const float *>(sum->data);
        double max_abs = 0.0, mean_abs = 0.0;
        for (int index = 0; index < 2048; ++index) {
            const double reference = captured.layers[layer].output[index];
            const double delta = static_cast<double>(actual[index]) - reference;
            max_abs = std::max(max_abs, std::abs(delta)); mean_abs += std::abs(delta);
            global_error += delta * delta; global_reference += reference * reference;
        }
        mean_abs /= 2048.0; global_max = std::max(global_max, max_abs); global_mean_sum += mean_abs;
        std::cout << (layer ? "," : "") << "{\"layer\":" << layer
                  << ",\"down_ggml_type\":" << down_types[layer]
                  << ",\"max_abs_error\":" << max_abs << ",\"mean_abs_error\":" << mean_abs << "}";
        ggml_free(direct);
    }
    close(fd);
    const double relative_l2 = std::sqrt(global_error / global_reference);
    std::cout << "],\"values_compared\":98304,\"max_abs_error\":" << global_max
              << ",\"mean_abs_error\":" << global_mean_sum / layer_count
              << ",\"relative_l2_error\":" << relative_l2
              << ",\"bit_for_bit_equal\":" << (global_max == 0.0 ? "true" : "false") << "}\n";
    dlclose(plugin);
    return std::isfinite(relative_l2) ? 0 : 13;
}
