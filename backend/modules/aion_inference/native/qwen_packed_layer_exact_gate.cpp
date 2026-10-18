#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <cstring>
#include <dlfcn.h>
#include <fcntl.h>
#include <iostream>
#include <unistd.h>
#include <vector>

#include "ggml-backend.h"
#include "ggml-cpu.h"
#include "ggml.h"
#include "llama.h"

using compute_function = ggml_status (*)(ggml_context *, ggml_cgraph *, int);

struct capture_state {
    int layer = 0;
    std::string topk_name;
    std::string weights_name;
    std::string gate_name;
    std::string output_name;
    std::array<int32_t, 8> route{};
    std::array<float, 8> gates{};
    std::array<float, 2048> input{};
    std::array<float, 2048> stock_output{};
    bool route_ok = false;
    bool gates_ok = false;
    bool input_ok = false;
    bool output_ok = false;
    int64_t batch_tokens = 0;
};

static void get_f32_vector(ggml_tensor * tensor, float * destination, size_t count) {
    ggml_backend_tensor_get_2d(tensor, destination, 0, count * sizeof(float), 1,
                               tensor->nb[1], count * sizeof(float));
}

static bool capture_layer_zero(ggml_tensor * tensor, bool ask, void * opaque) {
    const char * name = ggml_get_name(tensor);
    auto * state = static_cast<capture_state *>(opaque);
    const bool wanted = name == state->topk_name || name == state->weights_name ||
        name == state->gate_name || name == state->output_name;
    if (!wanted) return false;
    if (ask) return true;
    if (name == state->topk_name) {
        ggml_backend_tensor_get_2d(tensor, state->route.data(), 0, 8 * sizeof(int32_t),
                                   1, tensor->nb[1], 8 * sizeof(int32_t));
        state->route_ok = true;
    } else if (name == state->weights_name) {
        get_f32_vector(tensor, state->gates.data(), 8);
        state->gates_ok = true;
    } else if (name == state->gate_name) {
        for (ggml_tensor * source : tensor->src) {
            if (source != nullptr && source->type == GGML_TYPE_F32 &&
                    source->ne[0] == 2048) {
                get_f32_vector(source, state->input.data(), 2048);
                state->batch_tokens = source->ne[1];
                state->input_ok = true;
                break;
            }
        }
    } else {
        get_f32_vector(tensor, state->stock_output.data(), 2048);
        state->output_ok = true;
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
    if (argc != 7 && argc != 8) {
        std::cerr << "usage: exact_gate MODEL LAYER GATE_BASE UP_BASE DOWN_BASE DOWN_GGML_TYPE [PROMPT]\n";
        return 2;
    }
    const int layer = std::stoi(argv[2]);
    const off_t gate_base = std::stoll(argv[3]);
    const off_t up_base = std::stoll(argv[4]);
    const off_t down_base = std::stoll(argv[5]);
    const int down_type_number = std::stoi(argv[6]);
    if (layer < 0 || layer >= 48 ||
            (down_type_number != GGML_TYPE_Q4_K && down_type_number != GGML_TYPE_Q6_K)) return 2;
    const ggml_type down_type = static_cast<ggml_type>(down_type_number);
    capture_state captured;
    captured.layer = layer;
    captured.topk_name = "ffn_moe_topk-" + std::to_string(layer);
    captured.weights_name = "ffn_moe_weights_norm-" + std::to_string(layer);
    captured.gate_name = "ffn_moe_gate-" + std::to_string(layer);
    captured.output_name = "ffn_moe_out-" + std::to_string(layer);
    llama_backend_init();
    llama_model_params mp = llama_model_default_params();
    mp.n_gpu_layers = 0;
    mp.load_mode = LLAMA_LOAD_MODE_MMAP;
    mp.lazy_mode = LLAMA_LAZY_MODE_AUTO;
    mp.use_extra_bufts = false;
    llama_model * model = llama_model_load_from_file(argv[1], mp);
    if (model == nullptr) return 3;
    llama_context_params cp = llama_context_default_params();
    cp.n_ctx = 16;
    cp.n_batch = 16;
    cp.n_ubatch = 16;
    cp.n_threads = 8;
    cp.n_threads_batch = 8;
    cp.offload_kqv = false;
    cp.op_offload = false;
    cp.cb_eval = capture_layer_zero;
    cp.cb_eval_user_data = &captured;
    llama_context * context = llama_init_from_model(model, cp);
    if (context == nullptr) return 4;
    const std::string prompt = argc == 8 ? argv[7] : "Hello";
    const llama_vocab * vocab = llama_model_get_vocab(model);
    int32_t count = llama_tokenize(vocab, prompt.c_str(), prompt.size(), nullptr, 0, true, true);
    if (count >= 0) return 5;
    std::vector<llama_token> tokens(static_cast<size_t>(-count));
    count = llama_tokenize(vocab, prompt.c_str(), prompt.size(), tokens.data(), tokens.size(), true, true);
    const int decode_result = llama_decode(context, llama_batch_get_one(tokens.data(), count));
    llama_free(context);
    llama_model_free(model);
    llama_backend_free();
    if (decode_result != 0 || !captured.route_ok || !captured.gates_ok ||
            !captured.input_ok || !captured.output_ok) return 6;

    const int fd = open(argv[1], O_RDONLY);
    if (fd < 0) return 7;
    void * plugin = dlopen("/opt/homebrew/Cellar/ggml/0.23.0/libexec/libggml-cpu-apple_m2_m3.so",
                           RTLD_NOW | RTLD_LOCAL);
    if (plugin == nullptr) return 8;
    auto compute = reinterpret_cast<compute_function>(dlsym(plugin, "ggml_graph_compute_with_ctx"));
    if (compute == nullptr) return 9;
    std::vector<char> memory(256 * 1024 * 1024);
    ggml_context * direct = ggml_init({memory.size(), memory.data(), false});
    ggml_tensor * input = ggml_new_tensor_2d(direct, GGML_TYPE_F32, 2048, 1);
    std::copy(captured.input.begin(), captured.input.end(), static_cast<float *>(input->data));
    ggml_tensor * sum = nullptr;
    const off_t down_stride = down_type == GGML_TYPE_Q6_K ? 1290240 : 884736;
    for (int index = 0; index < 8; ++index) {
        const int expert = captured.route[index];
        ggml_tensor * gate = ggml_new_tensor_2d(direct, GGML_TYPE_Q4_K, 2048, 768);
        ggml_tensor * up = ggml_new_tensor_2d(direct, GGML_TYPE_Q4_K, 2048, 768);
        ggml_tensor * down = ggml_new_tensor_2d(direct, down_type, 768, 2048);
        if (!read_exact(fd, gate->data, ggml_nbytes(gate), gate_base + expert * 884736) ||
            !read_exact(fd, up->data, ggml_nbytes(up), up_base + expert * 884736) ||
            !read_exact(fd, down->data, ggml_nbytes(down), down_base + expert * down_stride)) return 10;
        ggml_tensor * hidden = ggml_mul(direct,
            ggml_silu(direct, ggml_mul_mat(direct, gate, input)),
            ggml_mul_mat(direct, up, input));
        ggml_tensor * output = ggml_scale(direct, ggml_mul_mat(direct, down, hidden),
                                           captured.gates[index]);
        sum = sum == nullptr ? output : ggml_add(direct, sum, output);
    }
    close(fd);
    ggml_cgraph * graph = ggml_new_graph_custom(direct, GGML_DEFAULT_GRAPH_SIZE, false);
    ggml_build_forward_expand(graph, sum);
    if (compute(direct, graph, 8) != GGML_STATUS_SUCCESS) return 11;
    const auto * actual = static_cast<const float *>(sum->data);
    double max_abs = 0.0;
    double mean_abs = 0.0;
    double stock_norm = 0.0;
    double error_norm = 0.0;
    for (int index = 0; index < 2048; ++index) {
        const double delta = static_cast<double>(actual[index]) - captured.stock_output[index];
        max_abs = std::max(max_abs, std::abs(delta));
        mean_abs += std::abs(delta);
        stock_norm += static_cast<double>(captured.stock_output[index]) * captured.stock_output[index];
        error_norm += delta * delta;
    }
    mean_abs /= 2048.0;
    const double relative_l2 = std::sqrt(error_norm / stock_norm);
    std::cout << "{\"schema\":\"aion.qwen3moe.packed-layer-exact-gate.v1\","
              << "\"layer\":" << layer << ",\"down_ggml_type\":" << down_type_number
              << ",\"batch_tokens\":" << captured.batch_tokens << ",\"route\":[";
    for (int i = 0; i < 8; ++i) std::cout << (i ? "," : "") << captured.route[i];
    std::cout << "],\"gates\":[";
    for (int i = 0; i < 8; ++i) std::cout << (i ? "," : "") << captured.gates[i];
    std::cout << "],\"max_abs_error\":" << max_abs << ",\"mean_abs_error\":"
              << mean_abs << ",\"relative_l2_error\":" << relative_l2 << "}\n";
    ggml_free(direct);
    dlclose(plugin);
    return std::isfinite(relative_l2) ? 0 : 12;
}
