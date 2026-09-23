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
    if (argc != 5) {
        std::cerr << "usage: mxfp4-to-q2-0 INPUT OUTPUT WIDTH THREADS\n";
        return 2;
    }
    void * plugin = dlopen(
        "/opt/homebrew/Cellar/ggml/0.23.0/libexec/libggml-cpu-apple_m2_m3.so",
        RTLD_NOW | RTLD_LOCAL);
    if (!plugin) return 3;
    auto compute = reinterpret_cast<compute_function>(
        dlsym(plugin, "ggml_graph_compute_with_ctx"));
    if (!compute) return 4;
    const int64_t width = std::stoll(argv[3]);
    std::vector<char> memory(96 * 1024 * 1024);
    auto * context = ggml_init({memory.size(), memory.data(), false});
    if (!context) return 5;
    auto * packed = ggml_new_tensor_2d(context, GGML_TYPE_MXFP4, width, width);
    if (!read_exact(argv[1], packed->data, ggml_nbytes(packed))) return 6;
    auto * unpacked = ggml_cast(context, packed, GGML_TYPE_F32);
    auto * graph = ggml_new_graph_custom(context, GGML_DEFAULT_GRAPH_SIZE, false);
    ggml_build_forward_expand(graph, unpacked);
    if (compute(context, graph, std::stoi(argv[4])) != GGML_STATUS_SUCCESS) return 7;
    const size_t output_bytes = ggml_row_size(GGML_TYPE_Q2_0, width) * width;
    std::vector<char> quantized(output_bytes);
    const size_t written = ggml_quantize_chunk(
        GGML_TYPE_Q2_0, static_cast<const float *>(unpacked->data), quantized.data(),
        0, width, width, nullptr);
    if (written != output_bytes) return 8;
    std::ofstream output(argv[2], std::ios::binary | std::ios::trunc);
    output.write(quantized.data(), static_cast<std::streamsize>(quantized.size()));
    if (!output.good()) return 9;
    std::cout << "{\"source_bytes\":" << ggml_nbytes(packed)
              << ",\"q2_0_bytes\":" << output_bytes << "}\n";
    ggml_free(context);
    dlclose(plugin);
    return 0;
}
