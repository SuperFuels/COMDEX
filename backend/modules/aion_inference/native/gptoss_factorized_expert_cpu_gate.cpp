#include <dlfcn.h>
#include <fstream>
#include <iostream>
#include <string>
#include <vector>

#include "ggml.h"

using compute_function = ggml_status (*)(ggml_context *, ggml_cgraph *, int);

static bool read_exact(const char * path, void * target, size_t expected) {
    std::ifstream input(path, std::ios::binary | std::ios::ate);
    if (!input || static_cast<size_t>(input.tellg()) != expected) return false;
    input.seekg(0);
    input.read(static_cast<char *>(target), static_cast<std::streamsize>(expected));
    return input.good();
}

int main(int argc, char ** argv) {
    if (argc != 13) {
        std::cerr << "usage: factorized GATE_V GATE_U GATE_B UP_V UP_U UP_B "
                     "DOWN_V DOWN_U DOWN_B INPUT OUTPUT RANK\n";
        return 2;
    }
    void * plugin = dlopen(
        "/opt/homebrew/Cellar/ggml/0.23.0/libexec/libggml-cpu-apple_m2_m3.so",
        RTLD_NOW | RTLD_LOCAL);
    if (!plugin) return 3;
    auto compute = reinterpret_cast<compute_function>(
        dlsym(plugin, "ggml_graph_compute_with_ctx"));
    if (!compute) return 4;
    constexpr int64_t width = 2880;
    const int64_t rank = std::stoll(argv[12]);
    std::vector<char> memory(128 * 1024 * 1024);
    auto * context = ggml_init({memory.size(), memory.data(), false});
    if (!context) return 5;
    auto * gate_v = ggml_new_tensor_2d(context, GGML_TYPE_F16, width, rank);
    auto * gate_u = ggml_new_tensor_2d(context, GGML_TYPE_F16, rank, width);
    auto * gate_b = ggml_new_tensor_1d(context, GGML_TYPE_F32, width);
    auto * up_v = ggml_new_tensor_2d(context, GGML_TYPE_F16, width, rank);
    auto * up_u = ggml_new_tensor_2d(context, GGML_TYPE_F16, rank, width);
    auto * up_b = ggml_new_tensor_1d(context, GGML_TYPE_F32, width);
    auto * down_v = ggml_new_tensor_2d(context, GGML_TYPE_F16, width, rank);
    auto * down_u = ggml_new_tensor_2d(context, GGML_TYPE_F16, rank, width);
    auto * down_b = ggml_new_tensor_1d(context, GGML_TYPE_F32, width);
    ggml_tensor * values[] = {gate_v, gate_u, gate_b, up_v, up_u, up_b,
                              down_v, down_u, down_b};
    for (int index = 0; index < 9; ++index) {
        if (!read_exact(argv[index + 1], values[index]->data, ggml_nbytes(values[index]))) return 6;
    }
    auto * input = ggml_new_tensor_1d(context, GGML_TYPE_F32, width);
    if (!read_exact(argv[10], input->data, ggml_nbytes(input))) return 7;
    auto * gate = ggml_add(context,
        ggml_mul_mat(context, gate_u, ggml_mul_mat(context, gate_v, input)), gate_b);
    auto * up = ggml_add(context,
        ggml_mul_mat(context, up_u, ggml_mul_mat(context, up_v, input)), up_b);
    auto * hidden = ggml_swiglu_oai(context, gate, up, 1.702f, 7.0f);
    auto * output = ggml_add(context,
        ggml_mul_mat(context, down_u, ggml_mul_mat(context, down_v, hidden)), down_b);
    auto * graph = ggml_new_graph_custom(context, GGML_DEFAULT_GRAPH_SIZE, false);
    ggml_build_forward_expand(graph, output);
    if (compute(context, graph, 8) != GGML_STATUS_SUCCESS) return 8;
    std::ofstream result(argv[11], std::ios::binary | std::ios::trunc);
    result.write(static_cast<const char *>(output->data), ggml_nbytes(output));
    if (!result.good()) return 9;
    std::cout << "{\"rank\":" << rank << ",\"factor_bytes\":"
              << (ggml_nbytes(gate_v) + ggml_nbytes(gate_u) + ggml_nbytes(up_v)
                  + ggml_nbytes(up_u) + ggml_nbytes(down_v) + ggml_nbytes(down_u))
              << "}\n";
    ggml_free(context);
    dlclose(plugin);
    return 0;
}
