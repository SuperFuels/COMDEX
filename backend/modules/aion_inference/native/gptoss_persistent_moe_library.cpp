#include <chrono>
#include <cmath>
#include <cstring>
#include <dlfcn.h>
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
