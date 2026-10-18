#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstdlib>
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
    if (argc != 9) {
        std::cerr << "usage: gptoss_expert GATE_W GATE_B UP_W UP_B DOWN_W DOWN_B REPS THREADS\n";
        return 2;
    }
    void * plugin = dlopen(
        "/opt/homebrew/Cellar/ggml/0.23.0/libexec/libggml-cpu-apple_m2_m3.so",
        RTLD_NOW | RTLD_LOCAL);
    if (plugin == nullptr) return 3;
    auto compute = reinterpret_cast<compute_function>(
        dlsym(plugin, "ggml_graph_compute_with_ctx"));
    if (compute == nullptr) return 4;

    std::vector<char> memory(96 * 1024 * 1024);
    ggml_init_params parameters{memory.size(), memory.data(), false};
    ggml_context * context = ggml_init(parameters);
    if (context == nullptr) return 5;
    constexpr int64_t width = 2880;
    const char * batch_text = std::getenv("AION_BATCH");
    const int64_t batch = batch_text == nullptr ? 1 : std::stoll(batch_text);
    if (batch < 1) return 12;
    ggml_tensor * gate_w = ggml_new_tensor_2d(context, GGML_TYPE_MXFP4, width, width);
    ggml_tensor * gate_b = ggml_new_tensor_1d(context, GGML_TYPE_F32, width);
    ggml_tensor * up_w = ggml_new_tensor_2d(context, GGML_TYPE_MXFP4, width, width);
    ggml_tensor * up_b = ggml_new_tensor_1d(context, GGML_TYPE_F32, width);
    ggml_tensor * down_w = ggml_new_tensor_2d(context, GGML_TYPE_MXFP4, width, width);
    ggml_tensor * down_b = ggml_new_tensor_1d(context, GGML_TYPE_F32, width);
    ggml_tensor * tensors[] = {gate_w, gate_b, up_w, up_b, down_w, down_b};
    for (int index = 0; index < 6; ++index) {
        if (!read_exact(argv[index + 1], tensors[index]->data, ggml_nbytes(tensors[index]))) {
            std::cerr << "component size/read mismatch at argument " << index + 1 << "\n";
            return 6;
        }
    }
    ggml_tensor * input = ggml_new_tensor_2d(context, GGML_TYPE_F32, width, batch);
    auto * input_values = static_cast<float *>(input->data);
    const char * input_path = std::getenv("AION_INPUT_PATH");
    if (input_path != nullptr) {
        if (!read_exact(input_path, input->data, ggml_nbytes(input))) return 10;
    } else {
        for (int64_t row = 0; row < batch; ++row)
            for (int64_t index = 0; index < width; ++index)
                input_values[row*width+index] = std::sin(static_cast<float>(index) * 0.00390625f);
    }
    ggml_tensor * gate = ggml_add(context, ggml_mul_mat(context, gate_w, input), gate_b);
    ggml_tensor * up = ggml_add(context, ggml_mul_mat(context, up_w, input), up_b);
    ggml_tensor * hidden = ggml_swiglu_oai(context, gate, up, 1.702f, 7.0f);
    ggml_tensor * output = ggml_add(context, ggml_mul_mat(context, down_w, hidden), down_b);
    ggml_cgraph * graph = ggml_new_graph_custom(context, GGML_DEFAULT_GRAPH_SIZE, false);
    ggml_build_forward_expand(graph, output);
    const int threads = std::stoi(argv[8]);
    if (compute(context, graph, threads) != GGML_STATUS_SUCCESS) return 7;
    const int repetitions = std::stoi(argv[7]);
    std::vector<double> milliseconds;
    for (int iteration = 0; iteration < repetitions; ++iteration) {
        const auto begin = std::chrono::steady_clock::now();
        if (compute(context, graph, threads) != GGML_STATUS_SUCCESS) return 8;
        const auto end = std::chrono::steady_clock::now();
        milliseconds.push_back(std::chrono::duration<double, std::milli>(end - begin).count());
    }
    std::vector<double> ordered = milliseconds;
    std::sort(ordered.begin(), ordered.end());
    const auto * values = static_cast<const float *>(output->data);
    double checksum = 0.0;
    bool finite = true;
    for (int64_t index = 0; index < width*batch; ++index) {
        checksum += values[index];
        finite = finite && std::isfinite(values[index]);
    }
    const char * output_path = std::getenv("AION_OUTPUT_PATH");
    if (output_path != nullptr) {
        std::ofstream output_file(output_path, std::ios::binary | std::ios::trunc);
        output_file.write(reinterpret_cast<const char *>(values), ggml_nbytes(output));
        if (!output_file.good()) return 11;
    }
    std::cout << "{\"schema\":\"aion.gptoss.packed-expert-cpu.v1\","
              << "\"repetitions\":" << repetitions << ",\"threads\":" << threads
              << ",\"batch\":" << batch
              << ",\"weight_bytes\":"
              << (ggml_nbytes(gate_w) + ggml_nbytes(up_w) + ggml_nbytes(down_w))
              << ",\"p50_ms\":" << ordered[ordered.size() / 2]
              << ",\"p95_ms\":" << ordered[(95 * ordered.size() + 99) / 100 - 1]
              << ",\"checksum\":" << checksum << ",\"finite\":"
              << (finite ? "true" : "false") << "}\n";
    ggml_free(context);
    dlclose(plugin);
    return finite ? 0 : 9;
}
