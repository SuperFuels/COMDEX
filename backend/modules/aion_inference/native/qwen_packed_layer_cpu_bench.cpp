#include <algorithm>
#include <array>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <dlfcn.h>
#include <fcntl.h>
#include <iostream>
#include <sstream>
#include <string>
#include <unistd.h>
#include <vector>

#include "ggml-cpu.h"
#include "ggml.h"

using compute_function = ggml_status (*)(ggml_context *, ggml_cgraph *, int);

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
    if (argc != 9) {
        std::cerr << "usage: packed_layer MODEL REPS LAYER GATE_BASE UP_BASE DOWN_BASE DOWN_GGML_TYPE ROUTE_CSV\n";
        return 2;
    }
    const int layer = std::stoi(argv[3]);
    const off_t gate_base = std::stoll(argv[4]);
    const off_t up_base = std::stoll(argv[5]);
    const off_t down_base = std::stoll(argv[6]);
    std::array<int, 8> route{};
    const int down_type_number = std::stoi(argv[7]);
    if (down_type_number != GGML_TYPE_Q4_K && down_type_number != GGML_TYPE_Q6_K) return 2;
    const ggml_type down_type = static_cast<ggml_type>(down_type_number);
    std::istringstream route_stream(argv[8]);
    std::string route_part;
    int route_index = 0;
    while (std::getline(route_stream, route_part, ',')) {
        if (route_index >= 8) return 2;
        route[route_index++] = std::stoi(route_part);
    }
    if (route_index != 8) return 2;
    constexpr off_t gate_stride = 884736;
    constexpr off_t up_stride = 884736;
    const off_t down_stride = down_type == GGML_TYPE_Q6_K ? 1290240 : 884736;

    const int fd = open(argv[1], O_RDONLY);
    if (fd < 0) return 3;
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
    ggml_tensor * input = ggml_new_tensor_2d(context, GGML_TYPE_F32, 2048, 1);
    auto * input_values = static_cast<float *>(input->data);
    for (int index = 0; index < 2048; ++index) {
        input_values[index] = std::sin(static_cast<float>(index) * 0.0078125f);
    }

    ggml_tensor * sum = nullptr;
    size_t weight_bytes = 0;
    for (const int expert : route) {
        ggml_tensor * gate = ggml_new_tensor_2d(context, GGML_TYPE_Q4_K, 2048, 768);
        ggml_tensor * up = ggml_new_tensor_2d(context, GGML_TYPE_Q4_K, 2048, 768);
        ggml_tensor * down = ggml_new_tensor_2d(context, down_type, 768, 2048);
        if (!read_exact(fd, gate->data, ggml_nbytes(gate), gate_base + expert * gate_stride) ||
            !read_exact(fd, up->data, ggml_nbytes(up), up_base + expert * up_stride) ||
            !read_exact(fd, down->data, ggml_nbytes(down), down_base + expert * down_stride)) {
            return 7;
        }
        weight_bytes += ggml_nbytes(gate) + ggml_nbytes(up) + ggml_nbytes(down);
        ggml_tensor * gate_result = ggml_mul_mat(context, gate, input);
        ggml_tensor * up_result = ggml_mul_mat(context, up, input);
        ggml_tensor * activated = ggml_mul(context, ggml_silu(context, gate_result), up_result);
        ggml_tensor * output = ggml_mul_mat(context, down, activated);
        sum = sum == nullptr ? output : ggml_add(context, sum, output);
    }
    close(fd);
    ggml_cgraph * graph = ggml_new_graph_custom(context, GGML_DEFAULT_GRAPH_SIZE, false);
    ggml_build_forward_expand(graph, sum);
    for (int iteration = 0; iteration < 3; ++iteration) {
        if (compute(context, graph, 8) != GGML_STATUS_SUCCESS) return 8;
    }
    const int repetitions = std::stoi(argv[2]);
    std::vector<double> milliseconds;
    for (int iteration = 0; iteration < repetitions; ++iteration) {
        const auto begin = std::chrono::steady_clock::now();
        if (compute(context, graph, 8) != GGML_STATUS_SUCCESS) return 9;
        const auto end = std::chrono::steady_clock::now();
        milliseconds.push_back(std::chrono::duration<double, std::milli>(end - begin).count());
    }
    std::sort(milliseconds.begin(), milliseconds.end());
    const double p50 = milliseconds[milliseconds.size() / 2];
    const double p95 = milliseconds[(95 * milliseconds.size() + 99) / 100 - 1];
    const auto * output_values = static_cast<const float *>(sum->data);
    double checksum = 0.0;
    bool finite = true;
    for (int index = 0; index < 2048; ++index) {
        checksum += output_values[index];
        finite = finite && std::isfinite(output_values[index]);
    }
    std::cout << "{\"schema\":\"aion.qwen3moe.packed-layer-cpu.v1\","
              << "\"repetitions\":" << repetitions << ",\"layer\":" << layer
              << ",\"experts\":8,\"down_ggml_type\":" << down_type_number << ","
              << "\"weight_bytes\":" << weight_bytes << ",\"p50_ms\":" << p50
              << ",\"p95_ms\":" << p95 << ",\"expert_only_projected_tps_p50\":"
              << 1000.0 / (48.0 * p50) << ",\"checksum\":" << checksum
              << ",\"finite\":" << (finite ? "true" : "false") << "}\n";
    ggml_free(context);
    dlclose(plugin);
    return finite ? 0 : 10;
}
