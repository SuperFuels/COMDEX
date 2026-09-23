#include <algorithm>
#include <cmath>
#include <dlfcn.h>
#include <fstream>
#include <iostream>
#include <string>
#include <vector>

#include "ggml.h"

using compute_function = ggml_status (*)(ggml_context *, ggml_cgraph *, int);

static bool read_exact(const std::string & path, void * target, size_t expected) {
    std::ifstream input(path, std::ios::binary | std::ios::ate);
    if (!input || static_cast<size_t>(input.tellg()) != expected) return false;
    input.seekg(0);
    input.read(static_cast<char *>(target), static_cast<std::streamsize>(expected));
    return input.good();
}

static bool write_exact(const std::string & path, const void * source, size_t size) {
    std::ofstream output(path, std::ios::binary | std::ios::trunc);
    output.write(static_cast<const char *>(source), static_cast<std::streamsize>(size));
    return output.good();
}

static size_t file_size(const std::string & path) {
    std::ifstream input(path, std::ios::binary | std::ios::ate);
    return input ? static_cast<size_t>(input.tellg()) : 0;
}

int main(int argc, char ** argv) {
    const bool kv_mode = argc == 7;
    if (argc != 5 && !kv_mode) {
        std::cerr << "usage: attention COMPONENT_DIR OUTPUT_PREFIX INPUT_OR_DASH [POSITION KV_PREFIX] THREADS\n";
        return 2;
    }
    void * plugin = dlopen(
        "/opt/homebrew/Cellar/ggml/0.23.0/libexec/libggml-cpu-apple_m2_m3.so",
        RTLD_NOW | RTLD_LOCAL);
    if (plugin == nullptr) return 3;
    auto compute = reinterpret_cast<compute_function>(
        dlsym(plugin, "ggml_graph_compute_with_ctx"));
    if (compute == nullptr) return 4;
    std::vector<char> memory(256 * 1024 * 1024);
    ggml_context * context = ggml_init({memory.size(), memory.data(), false});
    if (context == nullptr) return 5;
    constexpr int64_t width = 2880;
    constexpr int64_t q_width = 4096;
    constexpr int64_t kv_width = 512;
    constexpr int64_t heads = 64;
    constexpr int64_t kv_heads = 8;
    constexpr int64_t head_width = 64;
    constexpr float epsilon = 1.0e-5f;
    const std::string root = argv[1];

    ggml_tensor * input = ggml_new_tensor_2d(context, GGML_TYPE_F32, width, 1);
    auto * input_values = static_cast<float *>(input->data);
    if (std::string(argv[3]) == "-") {
        for (int64_t i = 0; i < width; ++i) input_values[i] = std::sin(float(i) * 0.00390625f);
    } else if (!read_exact(argv[3], input->data, ggml_nbytes(input))) {
        return 6;
    }
    ggml_tensor * norm_w = ggml_new_tensor_1d(context, GGML_TYPE_F32, width);
    ggml_tensor * q_w = ggml_new_tensor_2d(context, GGML_TYPE_Q5_0, width, q_width);
    ggml_tensor * q_b = ggml_new_tensor_1d(context, GGML_TYPE_F32, q_width);
    ggml_tensor * k_w = ggml_new_tensor_2d(context, GGML_TYPE_Q8_0, width, kv_width);
    ggml_tensor * k_b = ggml_new_tensor_1d(context, GGML_TYPE_F32, kv_width);
    const std::string v_weight_path = root + "/v-weight.bin";
    const enum ggml_type v_type = file_size(v_weight_path) == 1013760
        ? GGML_TYPE_Q5_0 : GGML_TYPE_Q8_0;
    ggml_tensor * v_w = ggml_new_tensor_2d(context, v_type, width, kv_width);
    ggml_tensor * v_b = ggml_new_tensor_1d(context, GGML_TYPE_F32, kv_width);
    ggml_tensor * sinks = ggml_new_tensor_1d(context, GGML_TYPE_F32, heads);
    struct Item { ggml_tensor * tensor; const char * name; } items[] = {
        {norm_w,"attn-norm-weight"},{q_w,"q-weight"},{q_b,"q-bias"},
        {k_w,"k-weight"},{k_b,"k-bias"},{v_w,"v-weight"},{v_b,"v-bias"},
        {sinks,"attn-sinks-weight"},
    };
    size_t shared_bytes = 0;
    for (const auto & item : items) {
        if (!read_exact(root + "/" + item.name + ".bin", item.tensor->data,
                        ggml_nbytes(item.tensor))) return 7;
        shared_bytes += ggml_nbytes(item.tensor);
    }
    ggml_tensor * normalized = ggml_mul(context, ggml_rms_norm(context, input, epsilon), norm_w);
    ggml_tensor * q = ggml_add(context, ggml_mul_mat(context, q_w, normalized), q_b);
    ggml_tensor * k = ggml_add(context, ggml_mul_mat(context, k_w, normalized), k_b);
    ggml_tensor * v = ggml_add(context, ggml_mul_mat(context, v_w, normalized), v_b);
    const int position = kv_mode ? std::stoi(argv[4]) : 0;
    if (kv_mode) {
        ggml_tensor * pos = ggml_new_tensor_1d(context, GGML_TYPE_I32, 1);
        *static_cast<int32_t *>(pos->data) = position;
        q = ggml_rope_ext(context, ggml_reshape_3d(context, q, head_width, heads, 1),
                          pos, nullptr, head_width, GGML_ROPE_TYPE_NEOX, 4096,
                          150000.0f, 1.0f/32.0f, 1.0f, 1.0f, 32.0f, 1.0f);
        k = ggml_rope_ext(context, ggml_reshape_3d(context, k, head_width, kv_heads, 1),
                          pos, nullptr, head_width, GGML_ROPE_TYPE_NEOX, 4096,
                          150000.0f, 1.0f/32.0f, 1.0f, 1.0f, 32.0f, 1.0f);
    }
    ggml_cgraph * qkv_graph = ggml_new_graph_custom(context, GGML_DEFAULT_GRAPH_SIZE, false);
    ggml_build_forward_expand(qkv_graph, q);
    ggml_build_forward_expand(qkv_graph, k);
    ggml_build_forward_expand(qkv_graph, v);
    const int threads = std::stoi(argv[kv_mode ? 6 : 4]);
    if (compute(context, qkv_graph, threads) != GGML_STATUS_SUCCESS) return 8;

    // Attention sinks compete as an additional zero-value logit per query head.
    ggml_tensor * attended = ggml_new_tensor_1d(context, GGML_TYPE_F32, q_width);
    auto * attended_values = static_cast<float *>(attended->data);
    const auto * q_values = static_cast<const float *>(q->data);
    const auto * k_values = static_cast<const float *>(k->data);
    const auto * v_values = static_cast<const float *>(v->data);
    const auto * sink_values = static_cast<const float *>(sinks->data);
    const float scale = 1.0f / std::sqrt(float(head_width));
    const int tokens = position + 1;
    std::vector<float> key_cache(tokens * kv_width), value_cache(tokens * kv_width);
    if (kv_mode && position > 0) {
        if (!read_exact(std::string(argv[5]) + "-k.bin", key_cache.data(), position * kv_width * sizeof(float)) ||
            !read_exact(std::string(argv[5]) + "-v.bin", value_cache.data(), position * kv_width * sizeof(float))) return 9;
    }
    std::copy(k_values, k_values + kv_width, key_cache.begin() + position * kv_width);
    std::copy(v_values, v_values + kv_width, value_cache.begin() + position * kv_width);
    if (kv_mode) {
        if (!write_exact(std::string(argv[5]) + "-k.bin", key_cache.data(), key_cache.size()*sizeof(float)) ||
            !write_exact(std::string(argv[5]) + "-v.bin", value_cache.data(), value_cache.size()*sizeof(float))) return 10;
    }
    for (int64_t head = 0; head < heads; ++head) {
        const int64_t kv_head = head / (heads / kv_heads);
        std::vector<float> scores(tokens);
        float maximum = sink_values[head];
        for (int token = 0; token < tokens; ++token) {
            float score = 0.0f;
            for (int64_t d = 0; d < head_width; ++d) score += q_values[head*head_width+d] * key_cache[token*kv_width+kv_head*head_width+d];
            scores[token] = score * scale; maximum = std::max(maximum, scores[token]);
        }
        float denominator = std::exp(sink_values[head]-maximum);
        for (float score : scores) denominator += std::exp(score-maximum);
        for (int64_t d = 0; d < head_width; ++d) {
            float value=0.0f;
            for(int token=0;token<tokens;++token) value += std::exp(scores[token]-maximum)/denominator * value_cache[token*kv_width+kv_head*head_width+d];
            attended_values[head * head_width + d] = value;
        }
    }

    ggml_tensor * out_w = ggml_new_tensor_2d(context, GGML_TYPE_Q5_K, q_width, width);
    ggml_tensor * out_b = ggml_new_tensor_1d(context, GGML_TYPE_F32, width);
    ggml_tensor * post_norm_w = ggml_new_tensor_1d(context, GGML_TYPE_F32, width);
    Item tail[] = {{out_w,"output-weight"},{out_b,"output-bias"},
                   {post_norm_w,"post-attention-norm-weight"}};
    for (const auto & item : tail) {
        if (!read_exact(root + "/" + item.name + ".bin", item.tensor->data,
                        ggml_nbytes(item.tensor))) return 9;
        shared_bytes += ggml_nbytes(item.tensor);
    }
    ggml_tensor * attention_output = ggml_add(
        context, ggml_mul_mat(context, out_w, attended), out_b);
    ggml_tensor * ffn_input = ggml_add(context, input, attention_output);
    ggml_tensor * router_input = ggml_mul(
        context, ggml_rms_norm(context, ffn_input, epsilon), post_norm_w);
    ggml_cgraph * output_graph = ggml_new_graph_custom(context, GGML_DEFAULT_GRAPH_SIZE, false);
    ggml_build_forward_expand(output_graph, router_input);
    if (compute(context, output_graph, threads) != GGML_STATUS_SUCCESS) return 10;
    const std::string prefix = argv[2];
    if (!write_exact(prefix + "-ffn-input.bin", ffn_input->data, ggml_nbytes(ffn_input)) ||
        !write_exact(prefix + "-router-input.bin", router_input->data, ggml_nbytes(router_input))) return 11;
    double ffn_checksum = 0.0, router_checksum = 0.0;
    bool finite = true;
    auto * ffn_values = static_cast<const float *>(ffn_input->data);
    auto * router_values = static_cast<const float *>(router_input->data);
    for (int64_t i = 0; i < width; ++i) {
        ffn_checksum += ffn_values[i]; router_checksum += router_values[i];
        finite &= std::isfinite(ffn_values[i]) && std::isfinite(router_values[i]);
    }
    std::cout << "{\"schema\":\"aion.gptoss.layer0-attention-cpu.v1\","
              << "\"position\":0,\"threads\":" << threads
              << ",\"shared_weight_bytes\":" << shared_bytes
              << ",\"ffn_input_checksum\":" << ffn_checksum
              << ",\"router_input_checksum\":" << router_checksum
              << ",\"finite\":" << (finite ? "true" : "false") << "}\n";
    ggml_free(context);
    dlclose(plugin);
    return finite ? 0 : 12;
}
