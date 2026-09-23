#include <chrono>
#include <cmath>
#include <cstring>
#include <dlfcn.h>
#include <vector>

#include "ggml.h"

using compute_function = ggml_status (*)(ggml_context *, ggml_cgraph *, int);

extern "C" int aion_gptoss_output(
        const void * weight_values, const float * norm_values,
        const float * hidden_values, float * logit_values, int threads,
        int * token_id, double * logit_checksum, double * elapsed_ms) {
    static void * plugin = dlopen(
        "/opt/homebrew/Cellar/ggml/0.23.0/libexec/libggml-cpu-apple_m2_m3.so",
        RTLD_NOW | RTLD_LOCAL);
    static compute_function compute = plugin ? reinterpret_cast<compute_function>(
        dlsym(plugin, "ggml_graph_compute_with_ctx")) : nullptr;
    // The arena is allocated once. The 615 MB immutable vocabulary tensor is a
    // read-only external view, so no weight bytes are copied into this arena.
    static std::vector<char> memory(768ULL * 1024 * 1024);
    static ggml_context * context = ggml_init({memory.size(), memory.data(), false});
    if (!compute) return 2;
    if (!context) return 3;
    ggml_reset(context);
    constexpr int64_t width = 2880;
    constexpr int64_t vocabulary = 201088;
    auto * weight = ggml_new_tensor_2d(context, GGML_TYPE_Q8_0, width, vocabulary);
    auto * norm = ggml_new_tensor_1d(context, GGML_TYPE_F32, width);
    auto * hidden = ggml_new_tensor_1d(context, GGML_TYPE_F32, width);
    weight->data = const_cast<void *>(weight_values);
    norm->data = const_cast<float *>(norm_values);
    hidden->data = const_cast<float *>(hidden_values);
    auto * normalized = ggml_mul(context, ggml_rms_norm(context, hidden, 1.0e-5f), norm);
    auto * logits = ggml_mul_mat(context, weight, normalized);
    auto * graph = ggml_new_graph_custom(context, GGML_DEFAULT_GRAPH_SIZE, false);
    ggml_build_forward_expand(graph, logits);
    const auto begin = std::chrono::steady_clock::now();
    if (compute(context, graph, threads) != GGML_STATUS_SUCCESS) return 4;
    *elapsed_ms = std::chrono::duration<double, std::milli>(
        std::chrono::steady_clock::now() - begin).count();
    const auto * values = static_cast<const float *>(logits->data);
    int best = 0;
    double checksum = 0.0;
    for (int index = 0; index < vocabulary; ++index) {
        if (!std::isfinite(values[index])) return 5;
        if (values[index] > values[best]) best = index;
        checksum += values[index];
    }
    std::memcpy(logit_values, values, vocabulary * sizeof(float));
    *token_id = best;
    *logit_checksum = checksum;
    return 0;
}
