#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <cstdlib>
#include <dlfcn.h>
#include <fcntl.h>
#include <iostream>
#include <numeric>
#include <string>
#include <unistd.h>
#include <vector>

#include "ggml-cpu.h"
#include "ggml.h"

using compute_function = ggml_status (*)(ggml_context *, ggml_cgraph *, int);

static bool read_exact(int descriptor, void * output, size_t bytes, off_t offset) {
    auto * destination = static_cast<char *>(output);
    size_t complete = 0;
    while (complete < bytes) {
        const ssize_t count = pread(descriptor, destination + complete, bytes - complete,
                                    offset + static_cast<off_t>(complete));
        if (count <= 0) return false;
        complete += static_cast<size_t>(count);
    }
    return true;
}

int main(int argc, char ** argv) {
    if (argc != 6 && argc != 8) {
        std::cerr << "usage: packed_expert MODEL GATE_OFFSET UP_OFFSET DOWN_OFFSET REPS [HIDDEN INTERMEDIATE]\n";
        return 2;
    }
    const int descriptor = open(argv[1], O_RDONLY);
    if (descriptor < 0) return 3;

    void * plugin = dlopen(
        "/opt/homebrew/Cellar/ggml/0.23.0/libexec/libggml-cpu-apple_m2_m3.so",
        RTLD_NOW | RTLD_LOCAL);
    if (plugin == nullptr) return 4;
    auto compute = reinterpret_cast<compute_function>(
        dlsym(plugin, "ggml_graph_compute_with_ctx"));
    if (compute == nullptr) return 5;

    std::vector<char> memory(64 * 1024 * 1024);
    ggml_init_params parameters{memory.size(), memory.data(), false};
    ggml_context * context = ggml_init(parameters);
    if (context == nullptr) return 6;

    const int hidden = argc == 8 ? std::stoi(argv[6]) : 2048;
    const int intermediate = argc == 8 ? std::stoi(argv[7]) : 768;
    ggml_tensor * gate = ggml_new_tensor_2d(context, GGML_TYPE_Q4_K, hidden, intermediate);
    ggml_tensor * up = ggml_new_tensor_2d(context, GGML_TYPE_Q4_K, hidden, intermediate);
    ggml_tensor * down = ggml_new_tensor_2d(context, GGML_TYPE_Q6_K, intermediate, hidden);
    if (!read_exact(descriptor, gate->data, ggml_nbytes(gate), std::stoll(argv[2])) ||
        !read_exact(descriptor, up->data, ggml_nbytes(up), std::stoll(argv[3])) ||
        !read_exact(descriptor, down->data, ggml_nbytes(down), std::stoll(argv[4]))) {
        return 7;
    }
    close(descriptor);

    ggml_tensor * input = ggml_new_tensor_2d(context, GGML_TYPE_F32, hidden, 1);
    auto * input_values = static_cast<float *>(input->data);
    for (int index = 0; index < hidden; ++index) {
        input_values[index] = std::sin(static_cast<float>(index) * 0.0078125f);
    }
    ggml_tensor * gate_result = ggml_mul_mat(context, gate, input);
    ggml_tensor * up_result = ggml_mul_mat(context, up, input);
    ggml_tensor * activated = ggml_mul(context, ggml_silu(context, gate_result), up_result);
    ggml_tensor * output = ggml_mul_mat(context, down, activated);
    ggml_cgraph * graph = ggml_new_graph_custom(context, GGML_DEFAULT_GRAPH_SIZE, false);
    ggml_build_forward_expand(graph, output);

    for (int iteration = 0; iteration < 3; ++iteration) {
        if (compute(context, graph, 8) != GGML_STATUS_SUCCESS) return 8;
    }
    const int repetitions = std::stoi(argv[5]);
    std::vector<double> milliseconds;
    milliseconds.reserve(repetitions);
    for (int iteration = 0; iteration < repetitions; ++iteration) {
        const auto begin = std::chrono::steady_clock::now();
        if (compute(context, graph, 8) != GGML_STATUS_SUCCESS) return 9;
        const auto end = std::chrono::steady_clock::now();
        milliseconds.push_back(std::chrono::duration<double, std::milli>(end - begin).count());
    }
    std::vector<double> ordered = milliseconds;
    std::sort(ordered.begin(), ordered.end());
    const double p50 = ordered[ordered.size() / 2];
    const double p95 = ordered[(95 * ordered.size() + 99) / 100 - 1];
    const auto * output_values = static_cast<const float *>(output->data);
    double checksum = 0.0;
    bool finite = true;
    for (int index = 0; index < hidden; ++index) {
        checksum += output_values[index];
        finite = finite && std::isfinite(output_values[index]);
    }
    std::cout << "{\"schema\":\"aion.qwen3moe.packed-expert-cpu.v1\","
              << "\"repetitions\":" << repetitions
              << ",\"hidden\":" << hidden << ",\"intermediate\":" << intermediate
              << ",\"weight_bytes\":"
              << (ggml_nbytes(gate) + ggml_nbytes(up) + ggml_nbytes(down))
              << ",\"p50_ms\":" << p50 << ",\"p95_ms\":" << p95
              << ",\"checksum\":" << checksum << ",\"finite\":"
              << (finite ? "true" : "false") << "}\n";

    ggml_free(context);
    dlclose(plugin);
    return finite ? 0 : 10;
}
