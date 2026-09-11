#include <dlfcn.h>
#include <fstream>
#include <iostream>
#include <string>
#include <vector>
#include <cstring>

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
    if (argc != 6) {
        std::cerr << "usage: mxfp4-to-padded-k INPUT OUTPUT q2_k|q3_k WIDTH THREADS\n";
        return 2;
    }
    const ggml_type type = std::string(argv[3]) == "q2_k" ? GGML_TYPE_Q2_K
                         : std::string(argv[3]) == "q3_k" ? GGML_TYPE_Q3_K
                         : GGML_TYPE_COUNT;
    if (type == GGML_TYPE_COUNT) return 3;
    void * plugin = dlopen(
        "/opt/homebrew/Cellar/ggml/0.23.0/libexec/libggml-cpu-apple_m2_m3.so",
        RTLD_NOW | RTLD_LOCAL);
    if (!plugin) return 4;
    auto compute = reinterpret_cast<compute_function>(
        dlsym(plugin, "ggml_graph_compute_with_ctx"));
    if (!compute) return 5;
    const int64_t width = std::stoll(argv[4]);
    constexpr int64_t padded = 3072;
    std::vector<char> memory(96 * 1024 * 1024);
    auto * context = ggml_init({memory.size(), memory.data(), false});
    if (!context) return 6;
    auto * packed = ggml_new_tensor_2d(context, GGML_TYPE_MXFP4, width, width);
    if (!read_exact(argv[1], packed->data, ggml_nbytes(packed))) return 7;
    auto * unpacked = ggml_cast(context, packed, GGML_TYPE_F32);
    auto * graph = ggml_new_graph_custom(context, GGML_DEFAULT_GRAPH_SIZE, false);
    ggml_build_forward_expand(graph, unpacked);
    if (compute(context, graph, std::stoi(argv[5])) != GGML_STATUS_SUCCESS) return 8;
    std::vector<float> padded_values(static_cast<size_t>(padded * padded), 0.0f);
    const auto * source = static_cast<const float *>(unpacked->data);
    for (int64_t row = 0; row < width; ++row)
        std::memcpy(padded_values.data() + row * padded, source + row * width,
                    width * sizeof(float));
    const size_t output_bytes = ggml_row_size(type, padded) * padded;
    std::vector<char> quantized(output_bytes);
    const size_t written = ggml_quantize_chunk(
        type, padded_values.data(), quantized.data(), 0, padded, padded, nullptr);
    if (written != output_bytes) return 9;
    std::ofstream output(argv[2], std::ios::binary | std::ios::trunc);
    output.write(quantized.data(), static_cast<std::streamsize>(quantized.size()));
    if (!output.good()) return 10;
    std::cout << "{\"source_bytes\":" << ggml_nbytes(packed)
              << ",\"quantized_bytes\":" << output_bytes << "}\n";
    ggml_free(context);
    dlclose(plugin);
    return 0;
}
