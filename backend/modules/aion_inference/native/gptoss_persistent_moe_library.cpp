#include <chrono>
#include <cmath>
#include <cstring>
#include <dlfcn.h>
#include <thread>
#include <vector>
#include "ggml.h"

using compute_function = ggml_status (*)(ggml_context *, ggml_cgraph *, int);

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
extern "C" int aion_gptoss_moe_finish_active(
        const float * ffn_input_values, const float * router_input_values,
        const void * const * components, const float * gates, int active_experts,
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
