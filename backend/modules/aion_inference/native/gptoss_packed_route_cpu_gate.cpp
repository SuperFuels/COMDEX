#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstdlib>
#include <dlfcn.h>
#include <fstream>
#include <iostream>
#include <sstream>
#include <string>
#include <vector>

#include "ggml.h"

using compute_function = ggml_status (*)(ggml_context *, ggml_cgraph *, int);

static std::vector<std::string> split(const std::string & value) {
    std::vector<std::string> result;
    std::stringstream stream(value);
    std::string item;
    while (std::getline(stream, item, ',')) result.push_back(item);
    return result;
}

static bool read_exact(const std::string & path, void * target, size_t expected) {
    std::ifstream input(path, std::ios::binary | std::ios::ate);
    if (!input || static_cast<size_t>(input.tellg()) != expected) return false;
    input.seekg(0);
    input.read(static_cast<char *>(target), static_cast<std::streamsize>(expected));
    return input.good();
}

int main(int argc, char ** argv) {
    if (argc != 6) {
        std::cerr << "usage: route COMPONENT_DIR ROUTE_CSV GATES_CSV REPS THREADS\n";
        return 2;
    }
    const auto routes = split(argv[2]);
    const auto gate_text = split(argv[3]);
    if (routes.size() != 4 || gate_text.size() != 4) return 3;
    std::vector<float> route_gates;
    for (const auto & item : gate_text) route_gates.push_back(std::stof(item));
    void * plugin = dlopen(
        "/opt/homebrew/Cellar/ggml/0.23.0/libexec/libggml-cpu-apple_m2_m3.so",
        RTLD_NOW | RTLD_LOCAL);
    if (plugin == nullptr) return 4;
    auto compute = reinterpret_cast<compute_function>(
        dlsym(plugin, "ggml_graph_compute_with_ctx"));
    if (compute == nullptr) return 5;
    std::vector<char> memory(256 * 1024 * 1024);
    ggml_context * context = ggml_init({memory.size(), memory.data(), false});
    if (context == nullptr) return 6;
    constexpr int64_t width = 2880;
    ggml_tensor * input = ggml_new_tensor_2d(context, GGML_TYPE_F32, width, 1);
    auto * input_values = static_cast<float *>(input->data);
    for (int64_t i = 0; i < width; ++i) input_values[i] = std::sin(float(i) * 0.00390625f);
    if (const char * input_path = std::getenv("AION_INPUT_PATH")) {
        if (!read_exact(input_path, input_values, width * sizeof(float))) return 12;
    }
    ggml_tensor * combined = nullptr;
    size_t packed_weight_bytes = 0;
    for (size_t position = 0; position < routes.size(); ++position) {
        ggml_tensor * gate_w = ggml_new_tensor_2d(context, GGML_TYPE_MXFP4, width, width);
        ggml_tensor * gate_b = ggml_new_tensor_1d(context, GGML_TYPE_F32, width);
        ggml_tensor * up_w = ggml_new_tensor_2d(context, GGML_TYPE_MXFP4, width, width);
        ggml_tensor * up_b = ggml_new_tensor_1d(context, GGML_TYPE_F32, width);
        ggml_tensor * down_w = ggml_new_tensor_2d(context, GGML_TYPE_MXFP4, width, width);
        ggml_tensor * down_b = ggml_new_tensor_1d(context, GGML_TYPE_F32, width);
        ggml_tensor * tensors[] = {gate_w, gate_b, up_w, up_b, down_w, down_b};
        const char * names[] = {"gate-weight", "gate-bias", "up-weight", "up-bias",
                                "down-weight", "down-bias"};
        for (int component = 0; component < 6; ++component) {
            const std::string path = std::string(argv[1]) + "/" + std::to_string(position)
                                   + "-" + names[component] + ".bin";
            if (!read_exact(path, tensors[component]->data, ggml_nbytes(tensors[component]))) return 7;
        }
        packed_weight_bytes += ggml_nbytes(gate_w) + ggml_nbytes(up_w) + ggml_nbytes(down_w);
        ggml_tensor * gate = ggml_add(context, ggml_mul_mat(context, gate_w, input), gate_b);
        ggml_tensor * up = ggml_add(context, ggml_mul_mat(context, up_w, input), up_b);
        ggml_tensor * hidden = ggml_swiglu_oai(context, gate, up, 1.702f, 7.0f);
        ggml_tensor * output = ggml_add(context, ggml_mul_mat(context, down_w, hidden), down_b);
        output = ggml_scale(context, output, route_gates[position]);
        combined = combined == nullptr ? output : ggml_add(context, combined, output);
    }
    ggml_cgraph * graph = ggml_new_graph_custom(context, GGML_DEFAULT_GRAPH_SIZE, false);
    ggml_build_forward_expand(graph, combined);
    const int threads = std::stoi(argv[5]);
    if (compute(context, graph, threads) != GGML_STATUS_SUCCESS) return 8;
    const int repetitions = std::stoi(argv[4]);
    const int cache_thrash_mib = std::getenv("AION_CPU_CACHE_THRASH_MIB")
        ? std::stoi(std::getenv("AION_CPU_CACHE_THRASH_MIB")) : 0;
    std::vector<unsigned char> cache_thrash(
        static_cast<size_t>(cache_thrash_mib) * 1024 * 1024);
    volatile unsigned long long cache_thrash_checksum = 0;
    std::vector<double> milliseconds;
    for (int i = 0; i < repetitions; ++i) {
        for (size_t offset = 0; offset < cache_thrash.size(); offset += 64) {
            cache_thrash[offset] = static_cast<unsigned char>(cache_thrash[offset] + i + 1);
            cache_thrash_checksum += cache_thrash[offset];
        }
        const auto begin = std::chrono::steady_clock::now();
        if (compute(context, graph, threads) != GGML_STATUS_SUCCESS) return 9;
        milliseconds.push_back(std::chrono::duration<double, std::milli>(
            std::chrono::steady_clock::now() - begin).count());
    }
    auto ordered = milliseconds;
    std::sort(ordered.begin(), ordered.end());
    const auto * values = static_cast<const float *>(combined->data);
    double checksum = 0.0;
    bool finite = true;
    for (int64_t i = 0; i < width; ++i) { checksum += values[i]; finite &= std::isfinite(values[i]); }
    if (const char * output_path = std::getenv("AION_OUTPUT_PATH")) {
        std::ofstream output_file(output_path, std::ios::binary | std::ios::trunc);
        output_file.write(reinterpret_cast<const char *>(values), width * sizeof(float));
        if (!output_file.good()) return 11;
    }
    std::cout << "{\"schema\":\"aion.gptoss.packed-route-cpu.v1\",\"route\":[";
    for (size_t i = 0; i < routes.size(); ++i) std::cout << (i ? "," : "") << routes[i];
    std::cout << "],\"gates\":[";
    for (size_t i = 0; i < route_gates.size(); ++i) std::cout << (i ? "," : "") << route_gates[i];
    std::cout << "],\"repetitions\":" << repetitions << ",\"threads\":" << threads
              << ",\"weight_bytes\":" << packed_weight_bytes
              << ",\"cache_thrash_mib\":" << cache_thrash_mib
              << ",\"cache_thrash_checksum\":" << cache_thrash_checksum
              << ",\"p50_ms\":" << ordered[ordered.size()/2]
              << ",\"p95_ms\":" << ordered[(95*ordered.size()+99)/100-1]
              << ",\"checksum\":" << checksum << ",\"finite\":"
              << (finite ? "true" : "false") << "}\n";
    ggml_free(context);
    dlclose(plugin);
    return finite ? 0 : 10;
}
