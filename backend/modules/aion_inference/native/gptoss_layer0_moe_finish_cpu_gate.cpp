#include <algorithm>
#include <cmath>
#include <dlfcn.h>
#include <fstream>
#include <iostream>
#include <sstream>
#include <string>
#include <vector>

#include "ggml.h"

using compute_function = ggml_status (*)(ggml_context *, ggml_cgraph *, int);

static std::vector<std::string> split(const std::string & value) {
    std::vector<std::string> result; std::stringstream stream(value); std::string item;
    while (std::getline(stream, item, ',')) result.push_back(item); return result;
}
static bool read_exact(const std::string & path, void * target, size_t expected) {
    std::ifstream input(path, std::ios::binary | std::ios::ate);
    if (!input || static_cast<size_t>(input.tellg()) != expected) return false;
    input.seekg(0); input.read(static_cast<char *>(target), static_cast<std::streamsize>(expected));
    return input.good();
}

int main(int argc, char ** argv) {
    if (argc != 8) {
        std::cerr << "usage: finish COMPONENT_DIR ROUTE_CSV GATES_CSV FFN_INPUT ROUTER_INPUT OUTPUT THREADS\n";
        return 2;
    }
    const auto routes = split(argv[2]); const auto gate_text = split(argv[3]);
    if (routes.size() != 4 || gate_text.size() != 4) return 3;
    std::vector<float> route_gates; for (const auto & item : gate_text) route_gates.push_back(std::stof(item));
    void * plugin = dlopen("/opt/homebrew/Cellar/ggml/0.23.0/libexec/libggml-cpu-apple_m2_m3.so", RTLD_NOW | RTLD_LOCAL);
    if (plugin == nullptr) return 4;
    auto compute = reinterpret_cast<compute_function>(dlsym(plugin, "ggml_graph_compute_with_ctx"));
    if (compute == nullptr) return 5;
    std::vector<char> memory(256 * 1024 * 1024);
    ggml_context * context = ggml_init({memory.size(), memory.data(), false});
    if (context == nullptr) return 6;
    constexpr int64_t width = 2880;
    ggml_tensor * ffn_input = ggml_new_tensor_1d(context, GGML_TYPE_F32, width);
    ggml_tensor * router_input = ggml_new_tensor_1d(context, GGML_TYPE_F32, width);
    if (!read_exact(argv[4], ffn_input->data, ggml_nbytes(ffn_input)) ||
        !read_exact(argv[5], router_input->data, ggml_nbytes(router_input))) return 7;
    ggml_tensor * combined = nullptr; size_t expert_weight_bytes = 0;
    for (size_t position = 0; position < 4; ++position) {
        ggml_tensor * gate_w = ggml_new_tensor_2d(context, GGML_TYPE_MXFP4, width, width);
        ggml_tensor * gate_b = ggml_new_tensor_1d(context, GGML_TYPE_F32, width);
        ggml_tensor * up_w = ggml_new_tensor_2d(context, GGML_TYPE_MXFP4, width, width);
        ggml_tensor * up_b = ggml_new_tensor_1d(context, GGML_TYPE_F32, width);
        ggml_tensor * down_w = ggml_new_tensor_2d(context, GGML_TYPE_MXFP4, width, width);
        ggml_tensor * down_b = ggml_new_tensor_1d(context, GGML_TYPE_F32, width);
        ggml_tensor * tensors[] = {gate_w,gate_b,up_w,up_b,down_w,down_b};
        const char * names[] = {"gate-weight","gate-bias","up-weight","up-bias","down-weight","down-bias"};
        for (int component = 0; component < 6; ++component) {
            const std::string path = std::string(argv[1]) + "/" + std::to_string(position) + "-" + names[component] + ".bin";
            if (!read_exact(path, tensors[component]->data, ggml_nbytes(tensors[component]))) return 8;
        }
        expert_weight_bytes += ggml_nbytes(gate_w)+ggml_nbytes(up_w)+ggml_nbytes(down_w);
        ggml_tensor * gate = ggml_add(context, ggml_mul_mat(context, gate_w, router_input), gate_b);
        ggml_tensor * up = ggml_add(context, ggml_mul_mat(context, up_w, router_input), up_b);
        ggml_tensor * hidden = ggml_swiglu_oai(context, gate, up, 1.702f, 7.0f);
        ggml_tensor * output = ggml_add(context, ggml_mul_mat(context, down_w, hidden), down_b);
        output = ggml_scale(context, output, route_gates[position]);
        combined = combined == nullptr ? output : ggml_add(context, combined, output);
    }
    ggml_tensor * block_output = ggml_add(context, ffn_input, combined);
    ggml_cgraph * graph = ggml_new_graph_custom(context, GGML_DEFAULT_GRAPH_SIZE, false);
    ggml_build_forward_expand(graph, block_output);
    if (compute(context, graph, std::stoi(argv[7])) != GGML_STATUS_SUCCESS) return 9;
    const auto * values = static_cast<const float *>(block_output->data);
    double checksum=0.0, l2=0.0; bool finite=true;
    for (int64_t i=0;i<width;++i) { checksum+=values[i]; l2+=double(values[i])*values[i]; finite&=std::isfinite(values[i]); }
    std::ofstream output_file(argv[6], std::ios::binary | std::ios::trunc);
    output_file.write(static_cast<const char *>(block_output->data), static_cast<std::streamsize>(ggml_nbytes(block_output)));
    if (!output_file.good()) return 10;
    std::cout << "{\"schema\":\"aion.gptoss.layer0-moe-finish-cpu.v1\",\"route\":[";
    for(size_t i=0;i<4;++i) std::cout<<(i?",":"")<<routes[i];
    std::cout << "],\"expert_weight_bytes\":" << expert_weight_bytes
              << ",\"output_checksum\":" << checksum << ",\"output_l2\":" << std::sqrt(l2)
              << ",\"finite\":" << (finite?"true":"false") << "}\n";
    ggml_free(context); dlclose(plugin); return finite?0:11;
}
