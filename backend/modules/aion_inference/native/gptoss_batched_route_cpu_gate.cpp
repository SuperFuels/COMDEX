#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstdlib>
#include <dlfcn.h>
#include <fstream>
#include <iostream>
#include <string>
#include <vector>
#include <fcntl.h>
#include <sys/mman.h>
#include <unistd.h>

#include "ggml.h"

using compute_function = ggml_status (*)(ggml_context *, ggml_cgraph *, int);

static bool read_exact(const std::string & path, void * target, size_t expected) {
    std::ifstream input(path, std::ios::binary | std::ios::ate);
    if (!input || static_cast<size_t>(input.tellg()) != expected) return false;
    input.seekg(0);
    input.read(static_cast<char *>(target), static_cast<std::streamsize>(expected));
    return input.good();
}

int main(int argc, char ** argv) {
    if (argc != 5) {
        std::cerr << "usage: batched-route COMPONENT_DIR GATES_CSV REPS THREADS\n";
        return 2;
    }
    std::vector<float> route_gates;
    std::string gate_text(argv[2]);
    size_t begin = 0;
    while (begin <= gate_text.size()) {
        const size_t end = gate_text.find(',', begin);
        route_gates.push_back(std::stof(gate_text.substr(begin, end - begin)));
        if (end == std::string::npos) break;
        begin = end + 1;
    }
    if (route_gates.size() != 4) return 3;
    void * plugin = dlopen(
        "/opt/homebrew/Cellar/ggml/0.23.0/libexec/libggml-cpu-apple_m2_m3.so",
        RTLD_NOW | RTLD_LOCAL);
    if (!plugin) return 4;
    auto compute = reinterpret_cast<compute_function>(
        dlsym(plugin, "ggml_graph_compute_with_ctx"));
    if (!compute) return 5;
    constexpr int64_t width = 2880;
    constexpr int64_t experts = 4;
    std::vector<char> memory(320 * 1024 * 1024);
    auto * context = ggml_init({memory.size(), memory.data(), false});
    if (!context) return 6;
    auto * gate_w = ggml_new_tensor_3d(context, GGML_TYPE_MXFP4, width, width, experts);
    auto * gate_b = ggml_new_tensor_3d(context, GGML_TYPE_F32, width, 1, experts);
    auto * up_w = ggml_new_tensor_3d(context, GGML_TYPE_MXFP4, width, width, experts);
    auto * up_b = ggml_new_tensor_3d(context, GGML_TYPE_F32, width, 1, experts);
    auto * down_w = ggml_new_tensor_3d(context, GGML_TYPE_MXFP4, width, width, experts);
    auto * down_b = ggml_new_tensor_3d(context, GGML_TYPE_F32, width, 1, experts);
    ggml_tensor * tensors[] = {gate_w, gate_b, up_w, up_b, down_w, down_b};
    const char * names[] = {"gate-weight", "gate-bias", "up-weight", "up-bias",
                            "down-weight", "down-bias"};
    const bool mmap_components = std::getenv("AION_MMAP_COMPONENTS") != nullptr;
    std::vector<std::pair<void *, size_t>> mappings;
    const auto mapping_started = std::chrono::steady_clock::now();
    for (int component = 0; component < 6; ++component) {
        const size_t slice_bytes = ggml_nbytes(tensors[component]) / experts;
        const size_t page = static_cast<size_t>(sysconf(_SC_PAGESIZE));
        const size_t stride = (slice_bytes + page - 1) / page * page;
        char * target = static_cast<char *>(tensors[component]->data);
        if (mmap_components) {
            target = static_cast<char *>(mmap(nullptr, stride * experts, PROT_NONE,
                MAP_PRIVATE | MAP_ANON, -1, 0));
            if (target == MAP_FAILED) return 12;
            mappings.emplace_back(target, stride * experts);
            tensors[component]->data = target;
            tensors[component]->nb[2] = stride;
        }
        for (int expert = 0; expert < experts; ++expert) {
            const std::string path = std::string(argv[1]) + "/" + std::to_string(expert)
                                   + "-" + names[component] + ".bin";
            if (mmap_components) {
                const int descriptor = open(path.c_str(), O_RDONLY);
                if (descriptor < 0) return 13;
                void * mapped = mmap(target + expert * stride, slice_bytes, PROT_READ,
                    MAP_PRIVATE | MAP_FIXED, descriptor, 0);
                close(descriptor);
                if (mapped == MAP_FAILED) return 14;
            } else if (!read_exact(path, target + expert * slice_bytes, slice_bytes)) {
                return 7;
            }
        }
    }
    const double mapping_ms = std::chrono::duration<double, std::milli>(
        std::chrono::steady_clock::now() - mapping_started).count();
    auto * input = ggml_new_tensor_3d(context, GGML_TYPE_F32, width, 1, experts);
    std::vector<float> one_input(width);
    if (const char * input_path = std::getenv("AION_INPUT_PATH")) {
        if (!read_exact(input_path, one_input.data(), width * sizeof(float))) return 8;
    } else {
        for (int64_t i = 0; i < width; ++i) one_input[i] = std::sin(float(i) * 0.00390625f);
    }
    for (int64_t expert = 0; expert < experts; ++expert) {
        std::copy(one_input.begin(), one_input.end(),
                  static_cast<float *>(input->data) + expert * width);
    }
    auto * gate = ggml_add(context, ggml_mul_mat(context, gate_w, input), gate_b);
    auto * up = ggml_add(context, ggml_mul_mat(context, up_w, input), up_b);
    auto * hidden = ggml_swiglu_oai(context, gate, up, 1.702f, 7.0f);
    auto * outputs = ggml_add(context, ggml_mul_mat(context, down_w, hidden), down_b);
    auto * slice0 = ggml_view_1d(context, outputs, width, 0);
    auto * slice1 = ggml_view_1d(context, outputs, width, outputs->nb[2]);
    auto * slice2 = ggml_view_1d(context, outputs, width, 2 * outputs->nb[2]);
    auto * slice3 = ggml_view_1d(context, outputs, width, 3 * outputs->nb[2]);
    auto * combined = ggml_add(context,
        ggml_add(context, ggml_scale(context, slice0, route_gates[0]),
                          ggml_scale(context, slice1, route_gates[1])),
        ggml_add(context, ggml_scale(context, slice2, route_gates[2]),
                          ggml_scale(context, slice3, route_gates[3])));
    auto * graph = ggml_new_graph_custom(context, GGML_DEFAULT_GRAPH_SIZE, false);
    ggml_build_forward_expand(graph, combined);
    const int threads = std::stoi(argv[4]);
    if (compute(context, graph, threads) != GGML_STATUS_SUCCESS) return 9;
    std::vector<double> milliseconds;
    for (int iteration = 0; iteration < std::stoi(argv[3]); ++iteration) {
        const auto started = std::chrono::steady_clock::now();
        if (compute(context, graph, threads) != GGML_STATUS_SUCCESS) return 10;
        milliseconds.push_back(std::chrono::duration<double, std::milli>(
            std::chrono::steady_clock::now() - started).count());
    }
    auto ordered = milliseconds;
    std::sort(ordered.begin(), ordered.end());
    if (const char * output_path = std::getenv("AION_OUTPUT_PATH")) {
        std::ofstream output(output_path, std::ios::binary | std::ios::trunc);
        output.write(static_cast<const char *>(combined->data), ggml_nbytes(combined));
        if (!output.good()) return 11;
    }
    std::cout << "{\"schema\":\"aion.gptoss.batched-route-cpu.v1\",\"mmap_components\":"
              << (mmap_components ? "true" : "false") << ",\"mapping_ms\":" << mapping_ms
              << ",\"p50_ms\":"
              << ordered[ordered.size()/2] << ",\"p95_ms\":"
              << ordered[(95*ordered.size()+99)/100-1] << "}\n";
    for (const auto & mapping : mappings) munmap(mapping.first, mapping.second);
    ggml_free(context);
    dlclose(plugin);
    return 0;
}
