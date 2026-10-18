#include <chrono>
#include <cmath>
#include <cstring>
#include <dlfcn.h>
#include <thread>
#include <vector>
#include <cstdint>
#include <unistd.h>
#include "ggml.h"

using compute_function = ggml_status (*)(ggml_context *, ggml_cgraph *, int);

// Persistent small-matrix router for the 128 x 2880 gate projection.  Calling
// a general BLAS dispatcher 36 times per token is disproportionately expensive
// for this shape, especially while the large expert pool is resident.  Keep the
// reduction explicit and deterministic; routing policy and top-k stay with the
// caller.
extern "C" int aion_gptoss_router_f32(
        const float * weights, const float * bias, const float * input,
        float * logits, double * elapsed_ms) {
    if (!weights || !bias || !input || !logits || !elapsed_ms) return 1;
    constexpr int experts = 128;
    constexpr int width = 2880;
    const auto begin = std::chrono::steady_clock::now();
    for (int expert = 0; expert < experts; ++expert) {
        const float * row = weights + expert * width;
        float sum = bias[expert];
        for (int index = 0; index < width; ++index)
            sum += row[index] * input[index];
        logits[expert] = sum;
    }
    *elapsed_ms = std::chrono::duration<double, std::milli>(
        std::chrono::steady_clock::now() - begin).count();
    return 0;
}

extern "C" int aion_gptoss_embedding_q5_0(
        const void * packed_row, float * output_values, int threads,
        double * elapsed_ms) {
    static void * plugin = dlopen(
        "/opt/homebrew/Cellar/ggml/0.23.0/libexec/libggml-cpu-apple_m2_m3.so",
        RTLD_NOW | RTLD_LOCAL);
    static compute_function compute = plugin ? reinterpret_cast<compute_function>(
        dlsym(plugin, "ggml_graph_compute_with_ctx")) : nullptr;
    static std::vector<char> memory(16 * 1024 * 1024);
    static ggml_context * context = ggml_init({memory.size(), memory.data(), false});
    if (!packed_row || !output_values || !elapsed_ms) return 1;
    if (!compute) return 2;
    if (!context) return 3;
    ggml_reset(context);
    constexpr int64_t width = 2880;
    auto * weight = ggml_new_tensor_2d(context, GGML_TYPE_Q5_0, width, 1);
    auto * index = ggml_new_tensor_1d(context, GGML_TYPE_I32, 1);
    weight->data = const_cast<void *>(packed_row);
    *static_cast<int32_t *>(index->data) = 0;
    auto * output = ggml_get_rows(context, weight, index);
    auto * graph = ggml_new_graph_custom(context, GGML_DEFAULT_GRAPH_SIZE, false);
    ggml_build_forward_expand(graph, output);
    const auto begin = std::chrono::steady_clock::now();
    const int status = compute(context, graph, threads);
    *elapsed_ms = std::chrono::duration<double, std::milli>(
        std::chrono::steady_clock::now() - begin).count();
    if (status != GGML_STATUS_SUCCESS) return 4;
    std::memcpy(output_values, output->data, width * sizeof(float));
    for (int64_t index_value = 0; index_value < width; ++index_value)
        if (!std::isfinite(output_values[index_value])) return 5;
    return 0;
}

extern "C" int aion_gptoss_prefault_components(
        const void * const * components, const size_t * component_sizes,
        int component_count, int workers, uint64_t * checksum,
        double * elapsed_ms) {
    if (!components || !component_sizes || !checksum || !elapsed_ms) return 1;
    if (component_count < 1 || component_count % 6 != 0 || workers < 1) return 2;
    const int experts = component_count / 6;
    const int worker_count = std::min(workers, experts);
    const size_t page_size = static_cast<size_t>(sysconf(_SC_PAGESIZE));
    if (page_size == 0) return 3;
    std::vector<uint64_t> partial(worker_count, 0);
    std::vector<std::thread> threads;
    const auto begin = std::chrono::steady_clock::now();
    for (int worker = 0; worker < worker_count; ++worker) {
        threads.emplace_back([&, worker]() {
            uint64_t sum = 0;
            for (int expert = worker; expert < experts; expert += worker_count) {
                for (int component = expert * 6; component < expert * 6 + 6; ++component) {
                    const auto * bytes = static_cast<const volatile uint8_t *>(
                        components[component]);
                    const size_t size = component_sizes[component];
                    for (size_t offset = 0; offset < size; offset += page_size)
                        sum += bytes[offset];
                    if (size > 0) sum += bytes[size - 1];
                }
            }
            partial[worker] = sum;
        });
    }
    for (auto & thread : threads) thread.join();
    uint64_t sum = 0;
    for (const auto value : partial) sum += value;
    *checksum = sum;
    *elapsed_ms = std::chrono::duration<double, std::milli>(
        std::chrono::steady_clock::now() - begin).count();
    return 0;
}

extern "C" int aion_gptoss_moe_finish(
        const float * ffn_input_values, const float * router_input_values,
        const void * const * components, const float * gates,
        float * output_values, int threads, double * elapsed_ms) {
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
    auto * ffn_input = ggml_new_tensor_1d(context, GGML_TYPE_F32, width);
    auto * router_input = ggml_new_tensor_1d(context, GGML_TYPE_F32, width);
    // The caller keeps every buffer alive until this function returns.  Point
    // read-only graph leaves at those buffers instead of copying roughly
    // 53 MiB of expert data into the arena for every layer invocation.
    ffn_input->data = const_cast<float *>(ffn_input_values);
    router_input->data = const_cast<float *>(router_input_values);
    ggml_tensor * combined = nullptr;
    for (int position=0; position<4; ++position) {
        auto * gate_w=ggml_new_tensor_2d(context,GGML_TYPE_MXFP4,width,width);
        auto * gate_b=ggml_new_tensor_1d(context,GGML_TYPE_F32,width);
        auto * up_w=ggml_new_tensor_2d(context,GGML_TYPE_MXFP4,width,width);
        auto * up_b=ggml_new_tensor_1d(context,GGML_TYPE_F32,width);
        auto * down_w=ggml_new_tensor_2d(context,GGML_TYPE_MXFP4,width,width);
        auto * down_b=ggml_new_tensor_1d(context,GGML_TYPE_F32,width);
        ggml_tensor * tensors[]={gate_w,gate_b,up_w,up_b,down_w,down_b};
        for(int component=0;component<6;++component)
            tensors[component]->data = const_cast<void *>(components[position*6+component]);
        auto * gate=ggml_add(context,ggml_mul_mat(context,gate_w,router_input),gate_b);
        auto * up=ggml_add(context,ggml_mul_mat(context,up_w,router_input),up_b);
        auto * hidden=ggml_swiglu_oai(context,gate,up,1.702f,7.0f);
        auto * expert=ggml_add(context,ggml_mul_mat(context,down_w,hidden),down_b);
        expert=ggml_scale(context,expert,gates[position]);
        combined=combined?ggml_add(context,combined,expert):expert;
    }
    auto * output=ggml_add(context,ffn_input,combined);
    auto * graph=ggml_new_graph_custom(context,GGML_DEFAULT_GRAPH_SIZE,false);
    ggml_build_forward_expand(graph,output);
    auto begin=std::chrono::steady_clock::now();
    int status=compute(context,graph,threads);
    *elapsed_ms=std::chrono::duration<double,std::milli>(std::chrono::steady_clock::now()-begin).count();
    if(status!=GGML_STATUS_SUCCESS)return 4;
    std::memcpy(output_values,output->data,width*sizeof(float));
    for(int i=0;i<width;++i)if(!std::isfinite(output_values[i]))return 5;
    return 0;
}

// Explicit quality-track entry point.  It retains the original packed expert
// arithmetic and reduction order, but permits a caller to execute only the
// strongest 1--4 routed experts.  The standard four-expert function above is
// deliberately unchanged so the exact track keeps its frozen ABI and maths.
static int moe_finish_active_impl(
        const float * ffn_input_values, const float * router_input_values,
        const void * const * components, const float * gates, int active_experts,
        const float * correction_values, float * output_values, int threads, double * elapsed_ms) {
    static void * plugin = dlopen(
        "/opt/homebrew/Cellar/ggml/0.23.0/libexec/libggml-cpu-apple_m2_m3.so",
        RTLD_NOW | RTLD_LOCAL);
    static compute_function compute = plugin ? reinterpret_cast<compute_function>(
        dlsym(plugin, "ggml_graph_compute_with_ctx")) : nullptr;
    static std::vector<char> memory(256 * 1024 * 1024);
    static ggml_context * context = ggml_init({memory.size(), memory.data(), false});
    if (!compute) return 2;
    if (!context) return 3;
    if (active_experts < 1 || active_experts > 4) return 6;
    ggml_reset(context);
    constexpr int64_t width = 2880;
    auto * ffn_input = ggml_new_tensor_1d(context, GGML_TYPE_F32, width);
    auto * router_input = ggml_new_tensor_1d(context, GGML_TYPE_F32, width);
    ffn_input->data = const_cast<float *>(ffn_input_values);
    router_input->data = const_cast<float *>(router_input_values);
    ggml_tensor * combined = nullptr;
    for (int position = 0; position < active_experts; ++position) {
        auto * gate_w = ggml_new_tensor_2d(context, GGML_TYPE_MXFP4, width, width);
        auto * gate_b = ggml_new_tensor_1d(context, GGML_TYPE_F32, width);
        auto * up_w = ggml_new_tensor_2d(context, GGML_TYPE_MXFP4, width, width);
        auto * up_b = ggml_new_tensor_1d(context, GGML_TYPE_F32, width);
        auto * down_w = ggml_new_tensor_2d(context, GGML_TYPE_MXFP4, width, width);
        auto * down_b = ggml_new_tensor_1d(context, GGML_TYPE_F32, width);
        ggml_tensor * tensors[] = {gate_w, gate_b, up_w, up_b, down_w, down_b};
        for (int component = 0; component < 6; ++component)
            tensors[component]->data = const_cast<void *>(components[position * 6 + component]);
        auto * gate = ggml_add(context, ggml_mul_mat(context, gate_w, router_input), gate_b);
        auto * up = ggml_add(context, ggml_mul_mat(context, up_w, router_input), up_b);
        auto * hidden = ggml_swiglu_oai(context, gate, up, 1.702f, 7.0f);
        auto * expert = ggml_add(context, ggml_mul_mat(context, down_w, hidden), down_b);
        expert = ggml_scale(context, expert, gates[position]);
        combined = combined ? ggml_add(context, combined, expert) : expert;
    }
    if (correction_values) {
        auto * correction = ggml_new_tensor_1d(context, GGML_TYPE_F32, width);
        correction->data = const_cast<float *>(correction_values);
        combined = ggml_add(context, combined, correction);
    }
    auto * output = ggml_add(context, ffn_input, combined);
    auto * graph = ggml_new_graph_custom(context, GGML_DEFAULT_GRAPH_SIZE, false);
    ggml_build_forward_expand(graph, output);
    const auto begin = std::chrono::steady_clock::now();
    const int status = compute(context, graph, threads);
    *elapsed_ms = std::chrono::duration<double, std::milli>(
        std::chrono::steady_clock::now() - begin).count();
    if (status != GGML_STATUS_SUCCESS) return 4;
    std::memcpy(output_values, output->data, width * sizeof(float));
    for (int64_t index = 0; index < width; ++index)
        if (!std::isfinite(output_values[index])) return 5;
    return 0;
}

extern "C" int aion_gptoss_moe_finish_active(
        const float * ffn_input_values, const float * router_input_values,
        const void * const * components, const float * gates, int active_experts,
        float * output_values, int threads, double * elapsed_ms) {
    return moe_finish_active_impl(ffn_input_values, router_input_values,
        components, gates, active_experts, nullptr, output_values, threads, elapsed_ms);
}

// Experimental 3+C4 path: append the already-gated correction BEFORE the
// residual, preserving the teacher's left-associated expert reduction order.
extern "C" int aion_gptoss_moe_finish_top3_correction(
        const float * ffn_input_values, const float * router_input_values,
        const void * const * components, const float * gates,
        const float * correction_values, float * output_values, int threads,
        double * elapsed_ms) {
    if (!correction_values) return 1;
    return moe_finish_active_impl(ffn_input_values, router_input_values,
        components, gates, 3, correction_values, output_values, threads, elapsed_ms);
}

// General ranked correction probe. Preserve the original left-associated
// reduction for one/two/three retained experts plus a gated last contribution.
// Existing exact and 3+C4 entry points remain unchanged.
extern "C" int aion_gptoss_moe_finish_ranked_correction(
        const float * ffn_input_values, const float * router_input_values,
        const void * const * components, const float * gates, int retained_experts,
        const float * correction_values, float * output_values, int threads,
        double * elapsed_ms) {
    if (retained_experts < 1 || retained_experts > 3) return 6;
    if (!ffn_input_values || !router_input_values || !components || !gates ||
            !correction_values || !output_values || !elapsed_ms) return 1;
    return moe_finish_active_impl(ffn_input_values, router_input_values,
        components, gates, retained_experts, correction_values, output_values,
        threads, elapsed_ms);
}

// Quality-track entry point using directly executable Q2_0 expert matrices.
// Router choice, gates, biases, non-linearity, reduction order and residual
// addition are unchanged; only the three selected weight representations differ.
extern "C" int aion_gptoss_moe_finish_q2_0(
        const float * ffn_input_values, const float * router_input_values,
        const void * const * components, const float * gates, int q2_projection_mask,
        float * output_values, int threads, double * elapsed_ms) {
    static void * plugin = dlopen(
        "/opt/homebrew/Cellar/ggml/0.23.0/libexec/libggml-cpu-apple_m2_m3.so",
        RTLD_NOW | RTLD_LOCAL);
    static compute_function compute = plugin ? reinterpret_cast<compute_function>(
        dlsym(plugin, "ggml_graph_compute_with_ctx")) : nullptr;
    static std::vector<char> memory(256 * 1024 * 1024);
    static ggml_context * context = ggml_init({memory.size(), memory.data(), false});
    if (!compute) return 2;
    if (!context) return 3;
    if (q2_projection_mask < 1 || q2_projection_mask > 7) return 6;
    ggml_reset(context);
    constexpr int64_t width = 2880;
    auto * ffn_input = ggml_new_tensor_1d(context, GGML_TYPE_F32, width);
    auto * router_input = ggml_new_tensor_1d(context, GGML_TYPE_F32, width);
    ffn_input->data = const_cast<float *>(ffn_input_values);
    router_input->data = const_cast<float *>(router_input_values);
    ggml_tensor * combined = nullptr;
    for (int position = 0; position < 4; ++position) {
        auto * gate_w = ggml_new_tensor_2d(context,
            q2_projection_mask & 1 ? GGML_TYPE_Q2_0 : GGML_TYPE_MXFP4, width, width);
        auto * gate_b = ggml_new_tensor_1d(context, GGML_TYPE_F32, width);
        auto * up_w = ggml_new_tensor_2d(context,
            q2_projection_mask & 2 ? GGML_TYPE_Q2_0 : GGML_TYPE_MXFP4, width, width);
        auto * up_b = ggml_new_tensor_1d(context, GGML_TYPE_F32, width);
        auto * down_w = ggml_new_tensor_2d(context,
            q2_projection_mask & 4 ? GGML_TYPE_Q2_0 : GGML_TYPE_MXFP4, width, width);
        auto * down_b = ggml_new_tensor_1d(context, GGML_TYPE_F32, width);
        ggml_tensor * tensors[] = {gate_w, gate_b, up_w, up_b, down_w, down_b};
        for (int component = 0; component < 6; ++component)
            tensors[component]->data = const_cast<void *>(components[position * 6 + component]);
        auto * gate = ggml_add(context, ggml_mul_mat(context, gate_w, router_input), gate_b);
        auto * up = ggml_add(context, ggml_mul_mat(context, up_w, router_input), up_b);
        auto * hidden = ggml_swiglu_oai(context, gate, up, 1.702f, 7.0f);
        auto * expert = ggml_add(context, ggml_mul_mat(context, down_w, hidden), down_b);
        expert = ggml_scale(context, expert, gates[position]);
        combined = combined ? ggml_add(context, combined, expert) : expert;
    }
    auto * output = ggml_add(context, ffn_input, combined);
    auto * graph = ggml_new_graph_custom(context, GGML_DEFAULT_GRAPH_SIZE, false);
    ggml_build_forward_expand(graph, output);
    const auto begin = std::chrono::steady_clock::now();
    const int status = compute(context, graph, threads);
    *elapsed_ms = std::chrono::duration<double, std::milli>(
        std::chrono::steady_clock::now() - begin).count();
    if (status != GGML_STATUS_SUCCESS) return 4;
    std::memcpy(output_values, output->data, width * sizeof(float));
    for (int64_t index = 0; index < width; ++index)
        if (!std::isfinite(output_values[index])) return 5;
    return 0;
}

// Quality-track ceiling bridge: preserve the strongest routed expert in the
// source MXFP4 representation while evaluating the three lower-gate experts
// from directly executable Q2_0 weights.  Router, gates, biases, non-linearity,
// expert ordering and residual addition remain unchanged.
extern "C" int aion_gptoss_moe_finish_top1_mxfp4_q2_0(
        const float * ffn_input_values, const float * router_input_values,
        const void * const * components, const float * gates,
        float * output_values, int threads, double * elapsed_ms) {
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
    auto * ffn_input = ggml_new_tensor_1d(context, GGML_TYPE_F32, width);
    auto * router_input = ggml_new_tensor_1d(context, GGML_TYPE_F32, width);
    ffn_input->data = const_cast<float *>(ffn_input_values);
    router_input->data = const_cast<float *>(router_input_values);
    ggml_tensor * combined = nullptr;
    for (int position = 0; position < 4; ++position) {
        const ggml_type weight_type = position == 0 ? GGML_TYPE_MXFP4 : GGML_TYPE_Q2_0;
        auto * gate_w = ggml_new_tensor_2d(context, weight_type, width, width);
        auto * gate_b = ggml_new_tensor_1d(context, GGML_TYPE_F32, width);
        auto * up_w = ggml_new_tensor_2d(context, weight_type, width, width);
        auto * up_b = ggml_new_tensor_1d(context, GGML_TYPE_F32, width);
        auto * down_w = ggml_new_tensor_2d(context, weight_type, width, width);
        auto * down_b = ggml_new_tensor_1d(context, GGML_TYPE_F32, width);
        ggml_tensor * tensors[] = {gate_w, gate_b, up_w, up_b, down_w, down_b};
        for (int component = 0; component < 6; ++component)
            tensors[component]->data = const_cast<void *>(components[position * 6 + component]);
        auto * gate = ggml_add(context, ggml_mul_mat(context, gate_w, router_input), gate_b);
        auto * up = ggml_add(context, ggml_mul_mat(context, up_w, router_input), up_b);
        auto * hidden = ggml_swiglu_oai(context, gate, up, 1.702f, 7.0f);
        auto * expert = ggml_add(context, ggml_mul_mat(context, down_w, hidden), down_b);
        expert = ggml_scale(context, expert, gates[position]);
        combined = combined ? ggml_add(context, combined, expert) : expert;
    }
    auto * output = ggml_add(context, ffn_input, combined);
    auto * graph = ggml_new_graph_custom(context, GGML_DEFAULT_GRAPH_SIZE, false);
    ggml_build_forward_expand(graph, output);
    const auto begin = std::chrono::steady_clock::now();
    const int status = compute(context, graph, threads);
    *elapsed_ms = std::chrono::duration<double, std::milli>(
        std::chrono::steady_clock::now() - begin).count();
    if (status != GGML_STATUS_SUCCESS) return 4;
    std::memcpy(output_values, output->data, width * sizeof(float));
    for (int64_t index = 0; index < width; ++index)
        if (!std::isfinite(output_values[index])) return 5;
    return 0;
}

// Quality-track top-three bridge: retain the three strongest routed experts
// in their original MXFP4 form and compact only the lowest-gate fourth expert.
// The router, four gates, biases, SwiGLU and reduction order remain unchanged.
extern "C" int aion_gptoss_moe_finish_top3_mxfp4_q2_0(
        const float * ffn_input_values, const float * router_input_values,
        const void * const * components, const float * gates,
        float * output_values, int threads, double * elapsed_ms) {
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
    auto * ffn_input = ggml_new_tensor_1d(context, GGML_TYPE_F32, width);
    auto * router_input = ggml_new_tensor_1d(context, GGML_TYPE_F32, width);
    ffn_input->data = const_cast<float *>(ffn_input_values);
    router_input->data = const_cast<float *>(router_input_values);
    ggml_tensor * combined = nullptr;
    for (int position = 0; position < 4; ++position) {
        const ggml_type weight_type = position < 3 ? GGML_TYPE_MXFP4 : GGML_TYPE_Q2_0;
        auto * gate_w = ggml_new_tensor_2d(context, weight_type, width, width);
        auto * gate_b = ggml_new_tensor_1d(context, GGML_TYPE_F32, width);
        auto * up_w = ggml_new_tensor_2d(context, weight_type, width, width);
        auto * up_b = ggml_new_tensor_1d(context, GGML_TYPE_F32, width);
        auto * down_w = ggml_new_tensor_2d(context, weight_type, width, width);
        auto * down_b = ggml_new_tensor_1d(context, GGML_TYPE_F32, width);
        ggml_tensor * tensors[] = {gate_w, gate_b, up_w, up_b, down_w, down_b};
        for (int component = 0; component < 6; ++component)
            tensors[component]->data = const_cast<void *>(components[position * 6 + component]);
        auto * gate = ggml_add(context,
            ggml_mul_mat(context, gate_w, router_input), gate_b);
        auto * up = ggml_add(context,
            ggml_mul_mat(context, up_w, router_input), up_b);
        auto * hidden = ggml_swiglu_oai(context, gate, up, 1.702f, 7.0f);
        auto * expert = ggml_add(context,
            ggml_mul_mat(context, down_w, hidden), down_b);
        expert = ggml_scale(context, expert, gates[position]);
        combined = combined ? ggml_add(context, combined, expert) : expert;
    }
    auto * output = ggml_add(context, ffn_input, combined);
    auto * graph = ggml_new_graph_custom(context, GGML_DEFAULT_GRAPH_SIZE, false);
    ggml_build_forward_expand(graph, output);
    const auto begin = std::chrono::steady_clock::now();
    const int status = compute(context, graph, threads);
    *elapsed_ms = std::chrono::duration<double, std::milli>(
        std::chrono::steady_clock::now() - begin).count();
    if (status != GGML_STATUS_SUCCESS) return 4;
    std::memcpy(output_values, output->data, width * sizeof(float));
    for (int64_t index = 0; index < width; ++index)
        if (!std::isfinite(output_values[index])) return 5;
    return 0;
}

// Accuracy-recovery quality track: preserve the three strongest routed experts
// exactly as MXFP4 at the model's native width, and encode only the fourth
// (lowest-gate) expert as padded Q3_K. The first three reductions retain their
// original order; the compact fourth contribution is sliced back to 2880.
extern "C" int aion_gptoss_moe_finish_top3_mxfp4_q3_k(
        const float * ffn_input_values, const float * router_input_values,
        const void * const * components, const float * gates,
        int quant_projection_mask, float * output_values, int threads,
        double * elapsed_ms) {
    static void * plugin = dlopen(
        "/opt/homebrew/Cellar/ggml/0.23.0/libexec/libggml-cpu-apple_m2_m3.so",
        RTLD_NOW | RTLD_LOCAL);
    static compute_function compute = plugin ? reinterpret_cast<compute_function>(
        dlsym(plugin, "ggml_graph_compute_with_ctx")) : nullptr;
    static std::vector<char> memory(320 * 1024 * 1024);
    static ggml_context * context = ggml_init({memory.size(), memory.data(), false});
    if (!compute) return 2;
    if (!context) return 3;
    if (quant_projection_mask < 1 || quant_projection_mask > 7) return 6;
    ggml_reset(context);
    constexpr int64_t width = 2880;
    constexpr int64_t padded = 3072;
    auto * ffn_input = ggml_new_tensor_1d(context, GGML_TYPE_F32, width);
    auto * router_input = ggml_new_tensor_1d(context, GGML_TYPE_F32, width);
    ffn_input->data = const_cast<float *>(ffn_input_values);
    router_input->data = const_cast<float *>(router_input_values);
    ggml_tensor * combined = nullptr;
    for (int position = 0; position < 3; ++position) {
        auto * gate_w = ggml_new_tensor_2d(context, GGML_TYPE_MXFP4, width, width);
        auto * gate_b = ggml_new_tensor_1d(context, GGML_TYPE_F32, width);
        auto * up_w = ggml_new_tensor_2d(context, GGML_TYPE_MXFP4, width, width);
        auto * up_b = ggml_new_tensor_1d(context, GGML_TYPE_F32, width);
        auto * down_w = ggml_new_tensor_2d(context, GGML_TYPE_MXFP4, width, width);
        auto * down_b = ggml_new_tensor_1d(context, GGML_TYPE_F32, width);
        ggml_tensor * tensors[] = {gate_w, gate_b, up_w, up_b, down_w, down_b};
        for (int component = 0; component < 6; ++component)
            tensors[component]->data = const_cast<void *>(components[position * 6 + component]);
        auto * gate = ggml_add(context, ggml_mul_mat(context, gate_w, router_input), gate_b);
        auto * up = ggml_add(context, ggml_mul_mat(context, up_w, router_input), up_b);
        auto * hidden = ggml_swiglu_oai(context, gate, up, 1.702f, 7.0f);
        auto * expert = ggml_add(context, ggml_mul_mat(context, down_w, hidden), down_b);
        expert = ggml_scale(context, expert, gates[position]);
        combined = combined ? ggml_add(context, combined, expert) : expert;
    }
    auto * padded_router = ggml_new_tensor_1d(context, GGML_TYPE_F32, padded);
    std::memset(padded_router->data, 0, padded * sizeof(float));
    std::memcpy(padded_router->data, router_input_values, width * sizeof(float));
    const bool compact_gate = quant_projection_mask & 1;
    const bool compact_up = quant_projection_mask & 2;
    const bool compact_down = quant_projection_mask & 4;
    auto * gate_w = ggml_new_tensor_2d(context,
        compact_gate ? GGML_TYPE_Q3_K : GGML_TYPE_MXFP4,
        compact_gate ? padded : width, compact_gate ? padded : width);
    auto * gate_b = ggml_new_tensor_1d(context, GGML_TYPE_F32,
        compact_gate ? padded : width);
    auto * up_w = ggml_new_tensor_2d(context,
        compact_up ? GGML_TYPE_Q3_K : GGML_TYPE_MXFP4,
        compact_up ? padded : width, compact_up ? padded : width);
    auto * up_b = ggml_new_tensor_1d(context, GGML_TYPE_F32,
        compact_up ? padded : width);
    auto * down_w = ggml_new_tensor_2d(context,
        compact_down ? GGML_TYPE_Q3_K : GGML_TYPE_MXFP4,
        compact_down ? padded : width, compact_down ? padded : width);
    auto * down_b = ggml_new_tensor_1d(context, GGML_TYPE_F32,
        compact_down ? padded : width);
    ggml_tensor * tensors[] = {gate_w, gate_b, up_w, up_b, down_w, down_b};
    for (int component = 0; component < 6; ++component)
        tensors[component]->data = const_cast<void *>(components[18 + component]);
    auto * gate = ggml_add(context, ggml_mul_mat(context, gate_w,
        compact_gate ? padded_router : router_input), gate_b);
    auto * up = ggml_add(context, ggml_mul_mat(context, up_w,
        compact_up ? padded_router : router_input), up_b);
    if (compact_gate) gate = ggml_view_1d(context, gate, width, 0);
    if (compact_up) up = ggml_view_1d(context, up, width, 0);
    auto * hidden = ggml_swiglu_oai(context, gate, up, 1.702f, 7.0f);
    auto * down_input = compact_down ? ggml_pad(context, hidden, padded - width, 0, 0, 0)
                                     : hidden;
    auto * fourth_full = ggml_add(context, ggml_mul_mat(context, down_w, down_input), down_b);
    auto * fourth = compact_down ? ggml_view_1d(context, fourth_full, width, 0)
                                 : fourth_full;
    fourth = ggml_scale(context, fourth, gates[3]);
    combined = ggml_add(context, combined, fourth);
    auto * output = ggml_add(context, ffn_input, combined);
    auto * graph = ggml_new_graph_custom(context, GGML_DEFAULT_GRAPH_SIZE, false);
    ggml_build_forward_expand(graph, output);
    const auto begin = std::chrono::steady_clock::now();
    const int status = compute(context, graph, threads);
    *elapsed_ms = std::chrono::duration<double, std::milli>(
        std::chrono::steady_clock::now() - begin).count();
    if (status != GGML_STATUS_SUCCESS) return 4;
    std::memcpy(output_values, output->data, width * sizeof(float));
    for (int64_t index = 0; index < width; ++index)
        if (!std::isfinite(output_values[index])) return 5;
    return 0;
}

// Quality-track mixed representation: keep selected routed experts in their
// original MXFP4 form and use padded Q3_K for selected projections of the
// remaining routed experts.  expert_mask addresses route positions 0..3 and
// projection_mask addresses gate/up/down as bits 0..2.  The caller supplies
// each component in the representation selected by those masks.
extern "C" int aion_gptoss_moe_finish_mixed_mxfp4_q3_k(
        const float * ffn_input_values, const float * router_input_values,
        const void * const * components, const float * gates,
        int expert_mask, int projection_mask, float * output_values, int threads,
        double * elapsed_ms) {
    static void * plugin = dlopen(
        "/opt/homebrew/Cellar/ggml/0.23.0/libexec/libggml-cpu-apple_m2_m3.so",
        RTLD_NOW | RTLD_LOCAL);
    static compute_function compute = plugin ? reinterpret_cast<compute_function>(
        dlsym(plugin, "ggml_graph_compute_with_ctx")) : nullptr;
    static std::vector<char> memory(384 * 1024 * 1024);
    static ggml_context * context = ggml_init({memory.size(), memory.data(), false});
    if (!compute) return 2;
    if (!context) return 3;
    if (expert_mask < 1 || expert_mask > 15) return 6;
    if (projection_mask < 1 || projection_mask > 7) return 7;
    ggml_reset(context);
    constexpr int64_t width = 2880;
    constexpr int64_t padded = 3072;
    auto * ffn_input = ggml_new_tensor_1d(context, GGML_TYPE_F32, width);
    auto * router_input = ggml_new_tensor_1d(context, GGML_TYPE_F32, width);
    ffn_input->data = const_cast<float *>(ffn_input_values);
    router_input->data = const_cast<float *>(router_input_values);
    auto * padded_router = ggml_new_tensor_1d(context, GGML_TYPE_F32, padded);
    std::memset(padded_router->data, 0, padded * sizeof(float));
    std::memcpy(padded_router->data, router_input_values, width * sizeof(float));
    ggml_tensor * combined = nullptr;
    for (int position = 0; position < 4; ++position) {
        const bool compact_expert = expert_mask & (1 << position);
        const bool compact_gate = compact_expert && (projection_mask & 1);
        const bool compact_up = compact_expert && (projection_mask & 2);
        const bool compact_down = compact_expert && (projection_mask & 4);
        auto * gate_w = ggml_new_tensor_2d(context,
            compact_gate ? GGML_TYPE_Q3_K : GGML_TYPE_MXFP4,
            compact_gate ? padded : width, compact_gate ? padded : width);
        auto * gate_b = ggml_new_tensor_1d(context, GGML_TYPE_F32,
            compact_gate ? padded : width);
        auto * up_w = ggml_new_tensor_2d(context,
            compact_up ? GGML_TYPE_Q3_K : GGML_TYPE_MXFP4,
            compact_up ? padded : width, compact_up ? padded : width);
        auto * up_b = ggml_new_tensor_1d(context, GGML_TYPE_F32,
            compact_up ? padded : width);
        auto * down_w = ggml_new_tensor_2d(context,
            compact_down ? GGML_TYPE_Q3_K : GGML_TYPE_MXFP4,
            compact_down ? padded : width, compact_down ? padded : width);
        auto * down_b = ggml_new_tensor_1d(context, GGML_TYPE_F32,
            compact_down ? padded : width);
        ggml_tensor * tensors[] = {gate_w, gate_b, up_w, up_b, down_w, down_b};
        for (int component = 0; component < 6; ++component)
            tensors[component]->data = const_cast<void *>(
                components[position * 6 + component]);
        auto * gate = ggml_add(context, ggml_mul_mat(context, gate_w,
            compact_gate ? padded_router : router_input), gate_b);
        auto * up = ggml_add(context, ggml_mul_mat(context, up_w,
            compact_up ? padded_router : router_input), up_b);
        if (compact_gate) gate = ggml_view_1d(context, gate, width, 0);
        if (compact_up) up = ggml_view_1d(context, up, width, 0);
        auto * hidden = ggml_swiglu_oai(context, gate, up, 1.702f, 7.0f);
        auto * down_input = compact_down
            ? ggml_pad(context, hidden, padded - width, 0, 0, 0) : hidden;
        auto * expert_full = ggml_add(context,
            ggml_mul_mat(context, down_w, down_input), down_b);
        auto * expert = compact_down
            ? ggml_view_1d(context, expert_full, width, 0) : expert_full;
        expert = ggml_scale(context, expert, gates[position]);
        combined = combined ? ggml_add(context, combined, expert) : expert;
    }
    auto * output = ggml_add(context, ffn_input, combined);
    auto * graph = ggml_new_graph_custom(context, GGML_DEFAULT_GRAPH_SIZE, false);
    ggml_build_forward_expand(graph, output);
    const auto begin = std::chrono::steady_clock::now();
    const int status = compute(context, graph, threads);
    *elapsed_ms = std::chrono::duration<double, std::milli>(
        std::chrono::steady_clock::now() - begin).count();
    if (status != GGML_STATUS_SUCCESS) return 4;
    std::memcpy(output_values, output->data, width * sizeof(float));
    for (int64_t index = 0; index < width; ++index)
        if (!std::isfinite(output_values[index])) return 5;
    return 0;
}

// Quality-track native-width mixed Q2_0 representation.  This is deliberately
// projection- and route-rank-selective: unchanged components remain MXFP4, so
// the accuracy cost of compacting lower-ranked expert matrices can be measured
// independently instead of quantising a complete expert as earlier probes did.
extern "C" int aion_gptoss_moe_finish_mixed_mxfp4_q2_0(
        const float * ffn_input_values, const float * router_input_values,
        const void * const * components, const float * gates,
        int expert_mask, int projection_mask, float * output_values, int threads,
        double * elapsed_ms) {
    static void * plugin = dlopen(
        "/opt/homebrew/Cellar/ggml/0.23.0/libexec/libggml-cpu-apple_m2_m3.so",
        RTLD_NOW | RTLD_LOCAL);
    static compute_function compute = plugin ? reinterpret_cast<compute_function>(
        dlsym(plugin, "ggml_graph_compute_with_ctx")) : nullptr;
    static std::vector<char> memory(320 * 1024 * 1024);
    static ggml_context * context = ggml_init({memory.size(), memory.data(), false});
    if (!compute) return 2;
    if (!context) return 3;
    if (expert_mask < 1 || expert_mask > 15) return 6;
    if (projection_mask < 1 || projection_mask > 7) return 7;
    ggml_reset(context);
    constexpr int64_t width = 2880;
    auto * ffn_input = ggml_new_tensor_1d(context, GGML_TYPE_F32, width);
    auto * router_input = ggml_new_tensor_1d(context, GGML_TYPE_F32, width);
    ffn_input->data = const_cast<float *>(ffn_input_values);
    router_input->data = const_cast<float *>(router_input_values);
    ggml_tensor * combined = nullptr;
    for (int position = 0; position < 4; ++position) {
        const bool compact_expert = expert_mask & (1 << position);
        const ggml_type gate_type = compact_expert && (projection_mask & 1)
            ? GGML_TYPE_Q2_0 : GGML_TYPE_MXFP4;
        const ggml_type up_type = compact_expert && (projection_mask & 2)
            ? GGML_TYPE_Q2_0 : GGML_TYPE_MXFP4;
        const ggml_type down_type = compact_expert && (projection_mask & 4)
            ? GGML_TYPE_Q2_0 : GGML_TYPE_MXFP4;
        auto * gate_w = ggml_new_tensor_2d(context, gate_type, width, width);
        auto * gate_b = ggml_new_tensor_1d(context, GGML_TYPE_F32, width);
        auto * up_w = ggml_new_tensor_2d(context, up_type, width, width);
        auto * up_b = ggml_new_tensor_1d(context, GGML_TYPE_F32, width);
        auto * down_w = ggml_new_tensor_2d(context, down_type, width, width);
        auto * down_b = ggml_new_tensor_1d(context, GGML_TYPE_F32, width);
        ggml_tensor * tensors[] = {gate_w, gate_b, up_w, up_b, down_w, down_b};
        for (int component = 0; component < 6; ++component)
            tensors[component]->data = const_cast<void *>(
                components[position * 6 + component]);
        auto * gate = ggml_add(context,
            ggml_mul_mat(context, gate_w, router_input), gate_b);
        auto * up = ggml_add(context,
            ggml_mul_mat(context, up_w, router_input), up_b);
        auto * hidden = ggml_swiglu_oai(context, gate, up, 1.702f, 7.0f);
        auto * expert = ggml_add(context,
            ggml_mul_mat(context, down_w, hidden), down_b);
        expert = ggml_scale(context, expert, gates[position]);
        combined = combined ? ggml_add(context, combined, expert) : expert;
    }
    auto * output = ggml_add(context, ffn_input, combined);
    auto * graph = ggml_new_graph_custom(context, GGML_DEFAULT_GRAPH_SIZE, false);
    ggml_build_forward_expand(graph, output);
    const auto begin = std::chrono::steady_clock::now();
    const int status = compute(context, graph, threads);
    *elapsed_ms = std::chrono::duration<double, std::milli>(
        std::chrono::steady_clock::now() - begin).count();
    if (status != GGML_STATUS_SUCCESS) return 4;
    std::memcpy(output_values, output->data, width * sizeof(float));
    for (int64_t index = 0; index < width; ++index)
        if (!std::isfinite(output_values[index])) return 5;
    return 0;
}

// Quality-track grouped quantisation on a zero-padded 3072-wide matrix.  The
// public hidden state remains 2880 values; padding exists only inside this ABI.
extern "C" int aion_gptoss_moe_finish_padded_k(
        const float * ffn_input_values, const float * router_input_values,
        const void * const * components, const float * gates, int q2_projection_mask,
        int quant_projection_mask, float * output_values, int threads,
        double * elapsed_ms) {
    static void * plugin = dlopen(
        "/opt/homebrew/Cellar/ggml/0.23.0/libexec/libggml-cpu-apple_m2_m3.so",
        RTLD_NOW | RTLD_LOCAL);
    static compute_function compute = plugin ? reinterpret_cast<compute_function>(
        dlsym(plugin, "ggml_graph_compute_with_ctx")) : nullptr;
    static std::vector<char> memory(320 * 1024 * 1024);
    static ggml_context * context = ggml_init({memory.size(), memory.data(), false});
    if (!compute) return 2;
    if (!context) return 3;
    if (q2_projection_mask < 0 || q2_projection_mask > 7) return 6;
    if (quant_projection_mask != 7) return 7;
    ggml_reset(context);
    constexpr int64_t width = 2880;
    constexpr int64_t padded = 3072;
    auto * ffn_input = ggml_new_tensor_1d(context, GGML_TYPE_F32, padded);
    auto * router_input = ggml_new_tensor_1d(context, GGML_TYPE_F32, padded);
    std::memset(ffn_input->data, 0, padded * sizeof(float));
    std::memset(router_input->data, 0, padded * sizeof(float));
    std::memcpy(ffn_input->data, ffn_input_values, width * sizeof(float));
    std::memcpy(router_input->data, router_input_values, width * sizeof(float));
    ggml_tensor * combined = nullptr;
    for (int position = 0; position < 4; ++position) {
        const ggml_type gate_type = q2_projection_mask & 1 ? GGML_TYPE_Q2_K : GGML_TYPE_Q3_K;
        const ggml_type up_type = q2_projection_mask & 2 ? GGML_TYPE_Q2_K : GGML_TYPE_Q3_K;
        const ggml_type down_type = q2_projection_mask & 4 ? GGML_TYPE_Q2_K : GGML_TYPE_Q3_K;
        auto * gate_w = ggml_new_tensor_2d(context, gate_type, padded, padded);
        auto * gate_b = ggml_new_tensor_1d(context, GGML_TYPE_F32, padded);
        auto * up_w = ggml_new_tensor_2d(context, up_type, padded, padded);
        auto * up_b = ggml_new_tensor_1d(context, GGML_TYPE_F32, padded);
        auto * down_w = ggml_new_tensor_2d(context, down_type, padded, padded);
        auto * down_b = ggml_new_tensor_1d(context, GGML_TYPE_F32, padded);
        ggml_tensor * tensors[] = {gate_w, gate_b, up_w, up_b, down_w, down_b};
        for (int component = 0; component < 6; ++component)
            tensors[component]->data = const_cast<void *>(components[position * 6 + component]);
        auto * gate = ggml_add(context, ggml_mul_mat(context, gate_w, router_input), gate_b);
        auto * up = ggml_add(context, ggml_mul_mat(context, up_w, router_input), up_b);
        auto * hidden = ggml_swiglu_oai(context, gate, up, 1.702f, 7.0f);
        auto * expert = ggml_add(context, ggml_mul_mat(context, down_w, hidden), down_b);
        expert = ggml_scale(context, expert, gates[position]);
        combined = combined ? ggml_add(context, combined, expert) : expert;
    }
    auto * output = ggml_add(context, ffn_input, combined);
    auto * graph = ggml_new_graph_custom(context, GGML_DEFAULT_GRAPH_SIZE, false);
    ggml_build_forward_expand(graph, output);
    const auto begin = std::chrono::steady_clock::now();
    const int status = compute(context, graph, threads);
    *elapsed_ms = std::chrono::duration<double, std::milli>(
        std::chrono::steady_clock::now() - begin).count();
    if (status != GGML_STATUS_SUCCESS) return 4;
    std::memcpy(output_values, output->data, width * sizeof(float));
    for (int64_t index = 0; index < width; ++index)
        if (!std::isfinite(output_values[index])) return 5;
    return 0;
}

extern "C" int aion_gptoss_moe_finish_parallel(
        const float * ffn_input_values, const float * router_input_values,
        const void * const * components, const float * gates,
        float * output_values, int threads, double * elapsed_ms) {
    static void * plugin = dlopen(
        "/opt/homebrew/Cellar/ggml/0.23.0/libexec/libggml-cpu-apple_m2_m3.so",
        RTLD_NOW | RTLD_LOCAL);
    static compute_function compute = plugin ? reinterpret_cast<compute_function>(
        dlsym(plugin, "ggml_graph_compute_with_ctx")) : nullptr;
    static std::vector<char> memories[4] = {
        std::vector<char>(64 * 1024 * 1024), std::vector<char>(64 * 1024 * 1024),
        std::vector<char>(64 * 1024 * 1024), std::vector<char>(64 * 1024 * 1024)};
    static ggml_context * contexts[4] = {
        ggml_init({memories[0].size(), memories[0].data(), false}),
        ggml_init({memories[1].size(), memories[1].data(), false}),
        ggml_init({memories[2].size(), memories[2].data(), false}),
        ggml_init({memories[3].size(), memories[3].data(), false})};
    if (!compute) return 2;
    for (auto * context : contexts) if (!context) return 3;
    constexpr int64_t width = 2880;
    std::vector<float> expert_outputs[4];
    int statuses[4] = {};
    const int expert_threads = std::max(1, threads / 4);
    auto begin = std::chrono::steady_clock::now();
    std::thread workers[4];
    for (int position = 0; position < 4; ++position) {
        workers[position] = std::thread([&, position]() {
            auto * context = contexts[position];
            ggml_reset(context);
            auto * router_input = ggml_new_tensor_1d(context, GGML_TYPE_F32, width);
            router_input->data = const_cast<float *>(router_input_values);
            auto * gate_w = ggml_new_tensor_2d(context, GGML_TYPE_MXFP4, width, width);
            auto * gate_b = ggml_new_tensor_1d(context, GGML_TYPE_F32, width);
            auto * up_w = ggml_new_tensor_2d(context, GGML_TYPE_MXFP4, width, width);
            auto * up_b = ggml_new_tensor_1d(context, GGML_TYPE_F32, width);
            auto * down_w = ggml_new_tensor_2d(context, GGML_TYPE_MXFP4, width, width);
            auto * down_b = ggml_new_tensor_1d(context, GGML_TYPE_F32, width);
            ggml_tensor * tensors[] = {gate_w, gate_b, up_w, up_b, down_w, down_b};
            for (int component = 0; component < 6; ++component)
                tensors[component]->data = const_cast<void *>(components[position * 6 + component]);
            auto * gate = ggml_add(context, ggml_mul_mat(context, gate_w, router_input), gate_b);
            auto * up = ggml_add(context, ggml_mul_mat(context, up_w, router_input), up_b);
            auto * hidden = ggml_swiglu_oai(context, gate, up, 1.702f, 7.0f);
            auto * expert = ggml_add(context, ggml_mul_mat(context, down_w, hidden), down_b);
            expert = ggml_scale(context, expert, gates[position]);
            auto * graph = ggml_new_graph_custom(context, GGML_DEFAULT_GRAPH_SIZE, false);
            ggml_build_forward_expand(graph, expert);
            statuses[position] = compute(context, graph, expert_threads);
            if (statuses[position] == GGML_STATUS_SUCCESS) {
                const auto * values = static_cast<const float *>(expert->data);
                expert_outputs[position].assign(values, values + width);
            }
        });
    }
    for (auto & worker : workers) worker.join();
    for (int position = 0; position < 4; ++position)
        if (statuses[position] != GGML_STATUS_SUCCESS) return 4;
    // Preserve the serial graph's left-associated expert reduction and final
    // residual addition order. This makes equivalence a testable gate rather
    // than silently accepting a parallel floating-point reassociation.
    for (int64_t index = 0; index < width; ++index) {
        float combined = expert_outputs[0][index] + expert_outputs[1][index];
        combined = combined + expert_outputs[2][index];
        combined = combined + expert_outputs[3][index];
        output_values[index] = ffn_input_values[index] + combined;
    }
    *elapsed_ms = std::chrono::duration<double, std::milli>(
        std::chrono::steady_clock::now() - begin).count();
    for (int64_t index = 0; index < width; ++index)
        if (!std::isfinite(output_values[index])) return 5;
    return 0;
}

// Exact rotating two-lane scheduler. Two experts calculate concurrently,
// followed by the next pair, reducing four-way memory-bandwidth contention.
extern "C" int aion_gptoss_moe_finish_pairwise(
        const float * ffn_input_values, const float * router_input_values,
        const void * const * components, const float * gates,
        float * output_values, int threads, double * elapsed_ms) {
    struct PersistentLane {
        std::vector<char> memory = std::vector<char>(128 * 1024 * 1024);
        ggml_context * context = nullptr;
        ggml_tensor * input = nullptr;
        ggml_tensor * components[6] = {};
        ggml_tensor * scaled = nullptr;
        ggml_cgraph * graph = nullptr;
    };
    static void * plugin = dlopen(
        "/opt/homebrew/Cellar/ggml/0.23.0/libexec/libggml-cpu-apple_m2_m3.so",
        RTLD_NOW | RTLD_LOCAL);
    static compute_function compute = plugin ? reinterpret_cast<compute_function>(
        dlsym(plugin, "ggml_graph_compute_with_ctx")) : nullptr;
    static PersistentLane lanes[2];
    if (!compute) return 2;
    constexpr int64_t width = 2880;
    for (auto & lane : lanes) {
        if (lane.context) continue;
        lane.context = ggml_init({lane.memory.size(), lane.memory.data(), false});
        if (!lane.context) return 3;
        lane.input = ggml_new_tensor_1d(lane.context, GGML_TYPE_F32, width);
        lane.components[0] = ggml_new_tensor_2d(lane.context, GGML_TYPE_MXFP4, width, width);
        lane.components[1] = ggml_new_tensor_1d(lane.context, GGML_TYPE_F32, width);
        lane.components[2] = ggml_new_tensor_2d(lane.context, GGML_TYPE_MXFP4, width, width);
        lane.components[3] = ggml_new_tensor_1d(lane.context, GGML_TYPE_F32, width);
        lane.components[4] = ggml_new_tensor_2d(lane.context, GGML_TYPE_MXFP4, width, width);
        lane.components[5] = ggml_new_tensor_1d(lane.context, GGML_TYPE_F32, width);
        auto * gate = ggml_add(lane.context,
            ggml_mul_mat(lane.context, lane.components[0], lane.input), lane.components[1]);
        auto * up = ggml_add(lane.context,
            ggml_mul_mat(lane.context, lane.components[2], lane.input), lane.components[3]);
        auto * hidden = ggml_swiglu_oai(lane.context, gate, up, 1.702f, 7.0f);
        auto * expert = ggml_add(lane.context,
            ggml_mul_mat(lane.context, lane.components[4], hidden), lane.components[5]);
        lane.scaled = ggml_scale(lane.context, expert, 1.0f);
        lane.graph = ggml_new_graph_custom(
            lane.context, GGML_DEFAULT_GRAPH_SIZE, false);
        ggml_build_forward_expand(lane.graph, lane.scaled);
    }
    std::vector<float> expert_outputs[4];
    int statuses[4] = {};
    const int expert_threads = std::max(1, threads / 2);
    const auto begin = std::chrono::steady_clock::now();
    for (int pair = 0; pair < 2; ++pair) {
        std::thread workers[2];
        for (int lane = 0; lane < 2; ++lane) {
            const int position = pair * 2 + lane;
            workers[lane] = std::thread([&, lane, position]() {
                auto & state = lanes[lane];
                state.input->data = const_cast<float *>(router_input_values);
                for (int component = 0; component < 6; ++component)
                    state.components[component]->data = const_cast<void *>(
                        components[position * 6 + component]);
                std::memcpy(state.scaled->op_params,
                            &gates[position], sizeof(float));
                statuses[position] = compute(
                    state.context, state.graph, expert_threads);
                if (statuses[position] == GGML_STATUS_SUCCESS) {
                    const auto * values = static_cast<const float *>(state.scaled->data);
                    expert_outputs[position].assign(values, values + width);
                }
            });
        }
        for (auto & worker : workers) worker.join();
    }
    for (int position = 0; position < 4; ++position)
        if (statuses[position] != GGML_STATUS_SUCCESS) return 4;
    for (int64_t index = 0; index < width; ++index) {
        float combined = expert_outputs[0][index] + expert_outputs[1][index];
        combined = combined + expert_outputs[2][index];
        combined = combined + expert_outputs[3][index];
        output_values[index] = ffn_input_values[index] + combined;
    }
    *elapsed_ms = std::chrono::duration<double, std::milli>(
        std::chrono::steady_clock::now() - begin).count();
    for (int64_t index = 0; index < width; ++index)
        if (!std::isfinite(output_values[index])) return 5;
    return 0;
}

extern "C" int aion_gptoss_moe_finish_reuse_graph(
        const float * ffn_input_values, const float * router_input_values,
        const void * const * components, const float * gates,
        float * output_values, int threads, double * elapsed_ms) {
    struct PersistentGraph {
        std::vector<char> memory = std::vector<char>(256 * 1024 * 1024);
        ggml_context * context = nullptr;
        ggml_tensor * ffn_input = nullptr;
        ggml_tensor * router_input = nullptr;
        ggml_tensor * component_tensors[24] = {};
        ggml_tensor * scale_tensors[4] = {};
        ggml_tensor * output = nullptr;
        ggml_cgraph * graph = nullptr;
    };
    static void * plugin = dlopen(
        "/opt/homebrew/Cellar/ggml/0.23.0/libexec/libggml-cpu-apple_m2_m3.so",
        RTLD_NOW | RTLD_LOCAL);
    static compute_function compute = plugin ? reinterpret_cast<compute_function>(
        dlsym(plugin, "ggml_graph_compute_with_ctx")) : nullptr;
    static PersistentGraph state;
    if (!compute) return 2;
    constexpr int64_t width = 2880;
    if (!state.context) {
        state.context = ggml_init({state.memory.size(), state.memory.data(), false});
        if (!state.context) return 3;
        state.ffn_input = ggml_new_tensor_1d(state.context, GGML_TYPE_F32, width);
        state.router_input = ggml_new_tensor_1d(state.context, GGML_TYPE_F32, width);
        ggml_tensor * combined = nullptr;
        for (int position = 0; position < 4; ++position) {
            auto * gate_w = ggml_new_tensor_2d(state.context, GGML_TYPE_MXFP4, width, width);
            auto * gate_b = ggml_new_tensor_1d(state.context, GGML_TYPE_F32, width);
            auto * up_w = ggml_new_tensor_2d(state.context, GGML_TYPE_MXFP4, width, width);
            auto * up_b = ggml_new_tensor_1d(state.context, GGML_TYPE_F32, width);
            auto * down_w = ggml_new_tensor_2d(state.context, GGML_TYPE_MXFP4, width, width);
            auto * down_b = ggml_new_tensor_1d(state.context, GGML_TYPE_F32, width);
            ggml_tensor * tensors[] = {gate_w, gate_b, up_w, up_b, down_w, down_b};
            for (int component = 0; component < 6; ++component)
                state.component_tensors[position * 6 + component] = tensors[component];
            auto * gate = ggml_add(state.context,
                ggml_mul_mat(state.context, gate_w, state.router_input), gate_b);
            auto * up = ggml_add(state.context,
                ggml_mul_mat(state.context, up_w, state.router_input), up_b);
            auto * hidden = ggml_swiglu_oai(state.context, gate, up, 1.702f, 7.0f);
            auto * expert = ggml_add(state.context,
                ggml_mul_mat(state.context, down_w, hidden), down_b);
            state.scale_tensors[position] = ggml_scale(state.context, expert, 1.0f);
            combined = combined ? ggml_add(state.context, combined,
                                            state.scale_tensors[position])
                                : state.scale_tensors[position];
        }
        state.output = ggml_add(state.context, state.ffn_input, combined);
        state.graph = ggml_new_graph_custom(
            state.context, GGML_DEFAULT_GRAPH_SIZE, false);
        ggml_build_forward_expand(state.graph, state.output);
    }
    state.ffn_input->data = const_cast<float *>(ffn_input_values);
    state.router_input->data = const_cast<float *>(router_input_values);
    for (int component = 0; component < 24; ++component)
        state.component_tensors[component]->data = const_cast<void *>(components[component]);
    for (int position = 0; position < 4; ++position)
        std::memcpy(state.scale_tensors[position]->op_params, &gates[position], sizeof(float));
    const auto begin = std::chrono::steady_clock::now();
    const int status = compute(state.context, state.graph, threads);
    *elapsed_ms = std::chrono::duration<double, std::milli>(
        std::chrono::steady_clock::now() - begin).count();
    if (status != GGML_STATUS_SUCCESS) return 4;
    std::memcpy(output_values, state.output->data, width * sizeof(float));
    for (int64_t index = 0; index < width; ++index)
        if (!std::isfinite(output_values[index])) return 5;
    return 0;
}

// Exact-track probe for amortising one resident expert over several independent
// activation rows. The packed MXFP4 weights remain unchanged. Each row retains
// its own residual and gate value; ggml performs the same row dot products but
// can reuse the packed matrix while it is hot in cache.
extern "C" int aion_gptoss_moe_finish_one_expert_batch(
        const float * ffn_input_values, const float * router_input_values,
        const void * const * components, const float * gates, int batch,
        float * output_values, int threads, double * elapsed_ms) {
    static void * plugin = dlopen(
        "/opt/homebrew/Cellar/ggml/0.23.0/libexec/libggml-cpu-apple_m2_m3.so",
        RTLD_NOW | RTLD_LOCAL);
    static compute_function compute = plugin ? reinterpret_cast<compute_function>(
        dlsym(plugin, "ggml_graph_compute_with_ctx")) : nullptr;
    static std::vector<char> memory(256 * 1024 * 1024);
    static ggml_context * context = ggml_init({memory.size(), memory.data(), false});
    if (!compute) return 2;
    if (!context) return 3;
    if (batch < 1 || batch > 64) return 6;
    ggml_reset(context);
    constexpr int64_t width = 2880;
    auto * ffn_input = ggml_new_tensor_2d(context, GGML_TYPE_F32, width, batch);
    auto * router_input = ggml_new_tensor_2d(context, GGML_TYPE_F32, width, batch);
    auto * gate_values = ggml_new_tensor_2d(context, GGML_TYPE_F32, 1, batch);
    ffn_input->data = const_cast<float *>(ffn_input_values);
    router_input->data = const_cast<float *>(router_input_values);
    gate_values->data = const_cast<float *>(gates);
    auto * gate_w = ggml_new_tensor_2d(context, GGML_TYPE_MXFP4, width, width);
    auto * gate_b = ggml_new_tensor_1d(context, GGML_TYPE_F32, width);
    auto * up_w = ggml_new_tensor_2d(context, GGML_TYPE_MXFP4, width, width);
    auto * up_b = ggml_new_tensor_1d(context, GGML_TYPE_F32, width);
    auto * down_w = ggml_new_tensor_2d(context, GGML_TYPE_MXFP4, width, width);
    auto * down_b = ggml_new_tensor_1d(context, GGML_TYPE_F32, width);
    ggml_tensor * tensors[] = {gate_w, gate_b, up_w, up_b, down_w, down_b};
    for (int component = 0; component < 6; ++component)
        tensors[component]->data = const_cast<void *>(components[component]);
    auto * gate = ggml_add(context, ggml_mul_mat(context, gate_w, router_input), gate_b);
    auto * up = ggml_add(context, ggml_mul_mat(context, up_w, router_input), up_b);
    auto * hidden = ggml_swiglu_oai(context, gate, up, 1.702f, 7.0f);
    auto * expert = ggml_add(context, ggml_mul_mat(context, down_w, hidden), down_b);
    auto * scaled = ggml_mul(context, expert, ggml_repeat(context, gate_values, expert));
    auto * output = ggml_add(context, ffn_input, scaled);
    auto * graph = ggml_new_graph_custom(context, GGML_DEFAULT_GRAPH_SIZE, false);
    ggml_build_forward_expand(graph, output);
    const auto begin = std::chrono::steady_clock::now();
    const int status = compute(context, graph, threads);
    *elapsed_ms = std::chrono::duration<double, std::milli>(
        std::chrono::steady_clock::now() - begin).count();
    if (status != GGML_STATUS_SUCCESS) return 4;
    std::memcpy(output_values, output->data, width * batch * sizeof(float));
    for (int64_t index = 0; index < width * batch; ++index)
        if (!std::isfinite(output_values[index])) return 5;
    return 0;
}

// Grouped block helper: evaluate one expert for several positions and return
// its gated contribution without a residual. Callers can then restore the
// original per-position expert reduction order exactly.
extern "C" int aion_gptoss_one_expert_contribution_batch(
        const float * router_input_values, const void * const * components,
        const float * gates, int batch, float * contribution_values,
        int threads, double * elapsed_ms) {
    static void * plugin = dlopen(
        "/opt/homebrew/Cellar/ggml/0.23.0/libexec/libggml-cpu-apple_m2_m3.so",
        RTLD_NOW | RTLD_LOCAL);
    static compute_function compute = plugin ? reinterpret_cast<compute_function>(
        dlsym(plugin, "ggml_graph_compute_with_ctx")) : nullptr;
    static std::vector<char> memory(256 * 1024 * 1024);
    static ggml_context * context = ggml_init({memory.size(), memory.data(), false});
    if (!compute) return 2;
    if (!context) return 3;
    if (batch < 1 || batch > 64) return 6;
    ggml_reset(context);
    constexpr int64_t width = 2880;
    auto * router_input = ggml_new_tensor_2d(context, GGML_TYPE_F32, width, batch);
    auto * gate_values = ggml_new_tensor_2d(context, GGML_TYPE_F32, 1, batch);
    router_input->data = const_cast<float *>(router_input_values);
    gate_values->data = const_cast<float *>(gates);
    auto * gate_w = ggml_new_tensor_2d(context, GGML_TYPE_MXFP4, width, width);
    auto * gate_b = ggml_new_tensor_1d(context, GGML_TYPE_F32, width);
    auto * up_w = ggml_new_tensor_2d(context, GGML_TYPE_MXFP4, width, width);
    auto * up_b = ggml_new_tensor_1d(context, GGML_TYPE_F32, width);
    auto * down_w = ggml_new_tensor_2d(context, GGML_TYPE_MXFP4, width, width);
    auto * down_b = ggml_new_tensor_1d(context, GGML_TYPE_F32, width);
    ggml_tensor * tensors[] = {gate_w, gate_b, up_w, up_b, down_w, down_b};
    for (int component = 0; component < 6; ++component)
        tensors[component]->data = const_cast<void *>(components[component]);
    auto * gate = ggml_add(context, ggml_mul_mat(context, gate_w, router_input), gate_b);
    auto * up = ggml_add(context, ggml_mul_mat(context, up_w, router_input), up_b);
    auto * hidden = ggml_swiglu_oai(context, gate, up, 1.702f, 7.0f);
    auto * expert = ggml_add(context, ggml_mul_mat(context, down_w, hidden), down_b);
    auto * scaled = ggml_mul(context, expert, ggml_repeat(context, gate_values, expert));
    auto * graph = ggml_new_graph_custom(context, GGML_DEFAULT_GRAPH_SIZE, false);
    ggml_build_forward_expand(graph, scaled);
    const auto begin = std::chrono::steady_clock::now();
    const int status = compute(context, graph, threads);
    *elapsed_ms = std::chrono::duration<double, std::milli>(
        std::chrono::steady_clock::now() - begin).count();
    if (status != GGML_STATUS_SUCCESS) return 4;
    std::memcpy(contribution_values, scaled->data, width * batch * sizeof(float));
    for (int64_t index = 0; index < width * batch; ++index)
        if (!std::isfinite(contribution_values[index])) return 5;
    return 0;
}

// Reusable single-position quality-track primitive.  The graph and arena are
// constructed once; each call changes only activation, packed-weight, bias and
// scalar-gate pointers.  This tests whether variable 2/3-expert execution is
// being dominated by graph construction rather than required MXFP4 work.
extern "C" int aion_gptoss_one_expert_contribution_reuse_graph(
        const float * router_input_values, const void * const * components,
        float gate_value, float * contribution_values,
        int threads, double * elapsed_ms) {
    struct PersistentContribution {
        std::vector<char> memory = std::vector<char>(128 * 1024 * 1024);
        ggml_context * context = nullptr;
        ggml_tensor * input = nullptr;
        ggml_tensor * components[6] = {};
        ggml_tensor * scaled = nullptr;
        ggml_cgraph * graph = nullptr;
    };
    static void * plugin = dlopen(
        "/opt/homebrew/Cellar/ggml/0.23.0/libexec/libggml-cpu-apple_m2_m3.so",
        RTLD_NOW | RTLD_LOCAL);
    static compute_function compute = plugin ? reinterpret_cast<compute_function>(
        dlsym(plugin, "ggml_graph_compute_with_ctx")) : nullptr;
    static PersistentContribution state;
    if (!compute) return 2;
    constexpr int64_t width = 2880;
    if (!state.context) {
        state.context = ggml_init({state.memory.size(), state.memory.data(), false});
        if (!state.context) return 3;
        state.input = ggml_new_tensor_1d(state.context, GGML_TYPE_F32, width);
        state.components[0] = ggml_new_tensor_2d(state.context, GGML_TYPE_MXFP4, width, width);
        state.components[1] = ggml_new_tensor_1d(state.context, GGML_TYPE_F32, width);
        state.components[2] = ggml_new_tensor_2d(state.context, GGML_TYPE_MXFP4, width, width);
        state.components[3] = ggml_new_tensor_1d(state.context, GGML_TYPE_F32, width);
        state.components[4] = ggml_new_tensor_2d(state.context, GGML_TYPE_MXFP4, width, width);
        state.components[5] = ggml_new_tensor_1d(state.context, GGML_TYPE_F32, width);
        auto * gate = ggml_add(state.context,
            ggml_mul_mat(state.context, state.components[0], state.input), state.components[1]);
        auto * up = ggml_add(state.context,
            ggml_mul_mat(state.context, state.components[2], state.input), state.components[3]);
        auto * hidden = ggml_swiglu_oai(state.context, gate, up, 1.702f, 7.0f);
        auto * expert = ggml_add(state.context,
            ggml_mul_mat(state.context, state.components[4], hidden), state.components[5]);
        state.scaled = ggml_scale(state.context, expert, 1.0f);
        state.graph = ggml_new_graph_custom(state.context, GGML_DEFAULT_GRAPH_SIZE, false);
        ggml_build_forward_expand(state.graph, state.scaled);
    }
    state.input->data = const_cast<float *>(router_input_values);
    for (int component = 0; component < 6; ++component)
        state.components[component]->data = const_cast<void *>(components[component]);
    std::memcpy(state.scaled->op_params, &gate_value, sizeof(float));
    const auto begin = std::chrono::steady_clock::now();
    const int status = compute(state.context, state.graph, threads);
    *elapsed_ms = std::chrono::duration<double, std::milli>(
        std::chrono::steady_clock::now() - begin).count();
    if (status != GGML_STATUS_SUCCESS) return 4;
    std::memcpy(contribution_values, state.scaled->data, width * sizeof(float));
    for (int64_t index = 0; index < width; ++index)
        if (!std::isfinite(contribution_values[index])) return 5;
    return 0;
}

// Exact-track probe for staging one expert at its true dependency boundary.
// Gate/up weights can be consumed before down weights have arrived.  The
// intermediate is the same F32 SwiGLU tensor that the unsplit ggml graph
// materialises, allowing delivery of the down projection to overlap useful
// gate/up arithmetic without changing packed values.
extern "C" int aion_gptoss_expert_gate_up(
        const float * router_input_values, const void * const * components,
        float * hidden_values, int threads, double * elapsed_ms) {
    static void * plugin = dlopen(
        "/opt/homebrew/Cellar/ggml/0.23.0/libexec/libggml-cpu-apple_m2_m3.so",
        RTLD_NOW | RTLD_LOCAL);
    static compute_function compute = plugin ? reinterpret_cast<compute_function>(
        dlsym(plugin, "ggml_graph_compute_with_ctx")) : nullptr;
    static std::vector<char> memory(128 * 1024 * 1024);
    static ggml_context * context = ggml_init({memory.size(), memory.data(), false});
    if (!compute) return 2;
    if (!context) return 3;
    ggml_reset(context);
    constexpr int64_t width = 2880;
    auto * input = ggml_new_tensor_1d(context, GGML_TYPE_F32, width);
    input->data = const_cast<float *>(router_input_values);
    auto * gate_w = ggml_new_tensor_2d(context, GGML_TYPE_MXFP4, width, width);
    auto * gate_b = ggml_new_tensor_1d(context, GGML_TYPE_F32, width);
    auto * up_w = ggml_new_tensor_2d(context, GGML_TYPE_MXFP4, width, width);
    auto * up_b = ggml_new_tensor_1d(context, GGML_TYPE_F32, width);
    ggml_tensor * tensors[] = {gate_w, gate_b, up_w, up_b};
    for (int component = 0; component < 4; ++component)
        tensors[component]->data = const_cast<void *>(components[component]);
    auto * gate = ggml_add(context, ggml_mul_mat(context, gate_w, input), gate_b);
    auto * up = ggml_add(context, ggml_mul_mat(context, up_w, input), up_b);
    auto * hidden = ggml_swiglu_oai(context, gate, up, 1.702f, 7.0f);
    auto * graph = ggml_new_graph_custom(context, GGML_DEFAULT_GRAPH_SIZE, false);
    ggml_build_forward_expand(graph, hidden);
    const auto begin = std::chrono::steady_clock::now();
    const int status = compute(context, graph, threads);
    *elapsed_ms = std::chrono::duration<double, std::milli>(
        std::chrono::steady_clock::now() - begin).count();
    if (status != GGML_STATUS_SUCCESS) return 4;
    std::memcpy(hidden_values, hidden->data, width * sizeof(float));
    for (int64_t index = 0; index < width; ++index)
        if (!std::isfinite(hidden_values[index])) return 5;
    return 0;
}

extern "C" int aion_gptoss_expert_down_contribution(
        const float * hidden_values, const void * const * components,
        float gate_value, float * contribution_values,
        int threads, double * elapsed_ms) {
    static void * plugin = dlopen(
        "/opt/homebrew/Cellar/ggml/0.23.0/libexec/libggml-cpu-apple_m2_m3.so",
        RTLD_NOW | RTLD_LOCAL);
    static compute_function compute = plugin ? reinterpret_cast<compute_function>(
        dlsym(plugin, "ggml_graph_compute_with_ctx")) : nullptr;
    static std::vector<char> memory(128 * 1024 * 1024);
    static ggml_context * context = ggml_init({memory.size(), memory.data(), false});
    if (!compute) return 2;
    if (!context) return 3;
    ggml_reset(context);
    constexpr int64_t width = 2880;
    auto * hidden = ggml_new_tensor_1d(context, GGML_TYPE_F32, width);
    hidden->data = const_cast<float *>(hidden_values);
    auto * down_w = ggml_new_tensor_2d(context, GGML_TYPE_MXFP4, width, width);
    auto * down_b = ggml_new_tensor_1d(context, GGML_TYPE_F32, width);
    auto * gate = ggml_new_tensor_1d(context, GGML_TYPE_F32, 1);
    down_w->data = const_cast<void *>(components[0]);
    down_b->data = const_cast<void *>(components[1]);
    gate->data = &gate_value;
    auto * expert = ggml_add(context, ggml_mul_mat(context, down_w, hidden), down_b);
    auto * scaled = ggml_mul(context, expert, ggml_repeat(context, gate, expert));
    auto * graph = ggml_new_graph_custom(context, GGML_DEFAULT_GRAPH_SIZE, false);
    ggml_build_forward_expand(graph, scaled);
    const auto begin = std::chrono::steady_clock::now();
    const int status = compute(context, graph, threads);
    *elapsed_ms = std::chrono::duration<double, std::milli>(
        std::chrono::steady_clock::now() - begin).count();
    if (status != GGML_STATUS_SUCCESS) return 4;
    std::memcpy(contribution_values, scaled->data, width * sizeof(float));
    for (int64_t index = 0; index < width; ++index)
        if (!std::isfinite(contribution_values[index])) return 5;
    return 0;
}

extern "C" int aion_gptoss_combine_four_contributions(
        const float * ffn_input_values, const float * contributions,
        int batch, float * output_values) {
    if (batch < 1 || batch > 64) return 6;
    constexpr int64_t width = 2880;
    for (int position = 0; position < batch; ++position) {
        const float * values = contributions + position * 4 * width;
        for (int64_t index = 0; index < width; ++index) {
            float combined = values[index] + values[width + index];
            combined = combined + values[2 * width + index];
            combined = combined + values[3 * width + index];
            output_values[position * width + index] =
                ffn_input_values[position * width + index] + combined;
        }
    }
    return 0;
}

// Exact heterogeneous multi-row verifier probe. Every position may reference
// a different ordered quartet. Weight leaves point directly at the caller's
// verified expert frames: no contiguous route slab or weight copy is created.
// One graph covers the complete block while retaining the scalar path's
// per-position expert reduction order.
extern "C" int aion_gptoss_moe_finish_heterogeneous_batch(
        const float * ffn_input_values, const float * router_input_values,
        const void * const * components, const float * gates, int batch,
        float * output_values, int threads, double * elapsed_ms) {
    static void * plugin = dlopen(
        "/opt/homebrew/Cellar/ggml/0.23.0/libexec/libggml-cpu-apple_m2_m3.so",
        RTLD_NOW | RTLD_LOCAL);
    static compute_function compute = plugin ? reinterpret_cast<compute_function>(
        dlsym(plugin, "ggml_graph_compute_with_ctx")) : nullptr;
    static std::vector<char> metadata_memory(8 * 1024 * 1024);
    static std::vector<char> compute_memory(128 * 1024 * 1024);
    static ggml_context * metadata = ggml_init(
        {metadata_memory.size(), metadata_memory.data(), true});
    static ggml_context * context = ggml_init(
        {compute_memory.size(), compute_memory.data(), false});
    if (!compute) return 2;
    if (!metadata || !context) return 3;
    if (batch < 1 || batch > 16) return 6;
    ggml_reset(metadata);
    ggml_reset(context);
    constexpr int64_t width = 2880;
    auto * graph = ggml_new_graph_custom(context, 4096, false);
    std::vector<ggml_tensor *> outputs;
    outputs.reserve(batch);
    for (int row = 0; row < batch; ++row) {
        auto * ffn_input = ggml_new_tensor_1d(metadata, GGML_TYPE_F32, width);
        auto * router_input = ggml_new_tensor_1d(metadata, GGML_TYPE_F32, width);
        ffn_input->data = const_cast<float *>(ffn_input_values + row * width);
        router_input->data = const_cast<float *>(router_input_values + row * width);
        ggml_tensor * combined = nullptr;
        for (int slot = 0; slot < 4; ++slot) {
            const int base = (row * 4 + slot) * 6;
            auto * gate_w = ggml_new_tensor_2d(
                metadata, GGML_TYPE_MXFP4, width, width);
            auto * gate_b = ggml_new_tensor_1d(metadata, GGML_TYPE_F32, width);
            auto * up_w = ggml_new_tensor_2d(
                metadata, GGML_TYPE_MXFP4, width, width);
            auto * up_b = ggml_new_tensor_1d(metadata, GGML_TYPE_F32, width);
            auto * down_w = ggml_new_tensor_2d(
                metadata, GGML_TYPE_MXFP4, width, width);
            auto * down_b = ggml_new_tensor_1d(metadata, GGML_TYPE_F32, width);
            ggml_tensor * tensors[] = {
                gate_w, gate_b, up_w, up_b, down_w, down_b};
            for (int component = 0; component < 6; ++component)
                tensors[component]->data = const_cast<void *>(
                    components[base + component]);
            auto * gate = ggml_add(context,
                ggml_mul_mat(context, gate_w, router_input), gate_b);
            auto * up = ggml_add(context,
                ggml_mul_mat(context, up_w, router_input), up_b);
            auto * hidden = ggml_swiglu_oai(
                context, gate, up, 1.702f, 7.0f);
            auto * expert = ggml_add(context,
                ggml_mul_mat(context, down_w, hidden), down_b);
            expert = ggml_scale(context, expert, gates[row * 4 + slot]);
            combined = combined ? ggml_add(context, combined, expert) : expert;
        }
        auto * output = ggml_add(context, ffn_input, combined);
        outputs.push_back(output);
        ggml_build_forward_expand(graph, output);
    }
    const auto begin = std::chrono::steady_clock::now();
    const int status = compute(context, graph, threads);
    *elapsed_ms = std::chrono::duration<double, std::milli>(
        std::chrono::steady_clock::now() - begin).count();
    if (status != GGML_STATUS_SUCCESS) return 4;
    for (int row = 0; row < batch; ++row)
        std::memcpy(output_values + row * width, outputs[row]->data,
                    width * sizeof(float));
    for (int64_t index = 0; index < width * batch; ++index)
        if (!std::isfinite(output_values[index])) return 5;
    return 0;
}

// Quality-track reducer for separately evaluated routed experts. Keeping the
// reduction native avoids Python temporaries and retains the active kernel's
// left-associated expert order.
extern "C" int aion_gptoss_combine_active_contributions(
        const float * ffn_input_values, const float * contributions,
        int active_experts, float * output_values) {
    if (active_experts < 1 || active_experts > 4) return 6;
    constexpr int64_t width = 2880;
    for (int64_t index = 0; index < width; ++index) {
        float combined = contributions[index];
        for (int position = 1; position < active_experts; ++position)
            combined = combined + contributions[position * width + index];
        output_values[index] = ffn_input_values[index] + combined;
    }
    return 0;
}
