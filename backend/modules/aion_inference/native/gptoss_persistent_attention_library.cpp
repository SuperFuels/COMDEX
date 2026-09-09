#include <algorithm>
#include <chrono>
#include <cmath>
#include <dlfcn.h>
#include <vector>

#include "ggml.h"

using compute_function = ggml_status (*)(ggml_context *, ggml_cgraph *, int);

extern "C" int aion_gptoss_attention_position_zero(
        const float * input_values, const void * const * components,
        int value_is_q5, float * ffn_output_values,
        float * router_output_values, int threads, double * elapsed_ms) {
    static void * plugin = dlopen(
        "/opt/homebrew/Cellar/ggml/0.23.0/libexec/libggml-cpu-apple_m2_m3.so",
        RTLD_NOW | RTLD_LOCAL);
    static compute_function compute = plugin ? reinterpret_cast<compute_function>(
        dlsym(plugin, "ggml_graph_compute_with_ctx")) : nullptr;
    static std::vector<char> memory(256 * 1024 * 1024);
    static ggml_context * context = ggml_init({memory.size(), memory.data(), false});
    if (!compute) return 2;
    if (!context) return 3;
    ggml_reset(context);

    constexpr int64_t width = 2880;
    constexpr int64_t q_width = 4096;
    constexpr int64_t kv_width = 512;
    constexpr int64_t heads = 64;
    constexpr int64_t kv_heads = 8;
    constexpr int64_t head_width = 64;
    constexpr float epsilon = 1.0e-5f;

    auto * input = ggml_new_tensor_2d(context, GGML_TYPE_F32, width, 1);
    auto * norm_w = ggml_new_tensor_1d(context, GGML_TYPE_F32, width);
    auto * q_w = ggml_new_tensor_2d(context, GGML_TYPE_Q5_0, width, q_width);
    auto * q_b = ggml_new_tensor_1d(context, GGML_TYPE_F32, q_width);
    auto * k_w = ggml_new_tensor_2d(context, GGML_TYPE_Q8_0, width, kv_width);
    auto * k_b = ggml_new_tensor_1d(context, GGML_TYPE_F32, kv_width);
    auto * v_w = ggml_new_tensor_2d(context, value_is_q5 ? GGML_TYPE_Q5_0 : GGML_TYPE_Q8_0, width, kv_width);
    auto * v_b = ggml_new_tensor_1d(context, GGML_TYPE_F32, kv_width);
    auto * sinks = ggml_new_tensor_1d(context, GGML_TYPE_F32, heads);
    auto * out_w = ggml_new_tensor_2d(context, GGML_TYPE_Q5_K, q_width, width);
    auto * out_b = ggml_new_tensor_1d(context, GGML_TYPE_F32, width);
    auto * post_norm_w = ggml_new_tensor_1d(context, GGML_TYPE_F32, width);
    input->data = const_cast<float *>(input_values);
    ggml_tensor * leaves[] = {norm_w,q_w,q_b,k_w,k_b,v_w,v_b,sinks,out_w,out_b,post_norm_w};
    for (int i=0;i<11;++i) leaves[i]->data = const_cast<void *>(components[i]);

    const auto begin = std::chrono::steady_clock::now();
    auto * normalized = ggml_mul(context, ggml_rms_norm(context, input, epsilon), norm_w);
    auto * q = ggml_add(context, ggml_mul_mat(context, q_w, normalized), q_b);
    auto * k = ggml_add(context, ggml_mul_mat(context, k_w, normalized), k_b);
    auto * v = ggml_add(context, ggml_mul_mat(context, v_w, normalized), v_b);
    auto * qkv_graph = ggml_new_graph_custom(context, GGML_DEFAULT_GRAPH_SIZE, false);
    ggml_build_forward_expand(qkv_graph, q);
    ggml_build_forward_expand(qkv_graph, k);
    ggml_build_forward_expand(qkv_graph, v);
    if (compute(context, qkv_graph, threads) != GGML_STATUS_SUCCESS) return 4;

    auto * attended = ggml_new_tensor_1d(context, GGML_TYPE_F32, q_width);
    auto * attended_values = static_cast<float *>(attended->data);
    const auto * q_values = static_cast<const float *>(q->data);
    const auto * k_values = static_cast<const float *>(k->data);
    const auto * v_values = static_cast<const float *>(v->data);
    const auto * sink_values = static_cast<const float *>(sinks->data);
    const float scale = 1.0f / std::sqrt(float(head_width));
    for (int64_t head=0;head<heads;++head) {
        const int64_t kv_head = head/(heads/kv_heads);
        float score=0.0f;
        for (int64_t d=0;d<head_width;++d)
            score += q_values[head*head_width+d]*k_values[kv_head*head_width+d];
        score *= scale;
        const float maximum=std::max(sink_values[head],score);
        const float probability=std::exp(score-maximum)/(
            std::exp(sink_values[head]-maximum)+std::exp(score-maximum));
        for (int64_t d=0;d<head_width;++d)
            attended_values[head*head_width+d]=probability*v_values[kv_head*head_width+d];
    }

    auto * attention_output = ggml_add(context, ggml_mul_mat(context, out_w, attended), out_b);
    auto * ffn_input = ggml_add(context, input, attention_output);
    auto * router_input = ggml_mul(context, ggml_rms_norm(context, ffn_input, epsilon), post_norm_w);
    auto * output_graph = ggml_new_graph_custom(context, GGML_DEFAULT_GRAPH_SIZE, false);
    ggml_build_forward_expand(output_graph, router_input);
    if (compute(context, output_graph, threads) != GGML_STATUS_SUCCESS) return 5;
    *elapsed_ms=std::chrono::duration<double,std::milli>(
        std::chrono::steady_clock::now()-begin).count();
    std::copy_n(static_cast<const float *>(ffn_input->data),width,ffn_output_values);
    std::copy_n(static_cast<const float *>(router_input->data),width,router_output_values);
    for (int64_t i=0;i<width;++i)
        if (!std::isfinite(ffn_output_values[i]) || !std::isfinite(router_output_values[i])) return 6;
    return 0;
}
