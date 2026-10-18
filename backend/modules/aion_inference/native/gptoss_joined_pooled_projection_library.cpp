#include <chrono>
#include <cmath>
#include <cstring>
#include <dlfcn.h>
#include <vector>
#include "ggml-cpu.h"
#include <cstdint>
using compute_function = ggml_status (*)(ggml_context *, ggml_cgraph *, int);

// Reuse CPU workers and aligned graph scratch across calls. No idle polling:
// other kernels must not compete with spinning workers between measurements.
static ggml_status pooled_compute(void * plugin, ggml_cgraph * graph, int threads) {
    using new_function=ggml_threadpool * (*)(ggml_threadpool_params *);
    using free_function=void (*)(ggml_threadpool *);
    using plan_function=ggml_cplan (*)(const ggml_cgraph *,int,ggml_threadpool *);
    using run_function=ggml_status (*)(ggml_cgraph *,ggml_cplan *);
    static auto make=reinterpret_cast<new_function>(dlsym(plugin,"ggml_threadpool_new"));
    static auto release=reinterpret_cast<free_function>(dlsym(plugin,"ggml_threadpool_free"));
    static auto make_plan=reinterpret_cast<plan_function>(dlsym(plugin,"ggml_graph_plan"));
    static auto run=reinterpret_cast<run_function>(dlsym(plugin,"ggml_graph_compute"));
    struct State {
        ggml_threadpool * pool=nullptr;
        int threads=0;
        std::vector<uint8_t> work;
        free_function release=nullptr;
        ~State(){if(pool && release)release(pool);}
    };
    static State state;
    if(!make || !release || !make_plan || !run)return GGML_STATUS_FAILED;
    if(state.threads!=threads) {
        if(state.pool)release(state.pool);
        auto params=ggml_threadpool_params_default(threads);
        params.poll=0;
        state.pool=make(&params);state.threads=threads;state.release=release;
        if(!state.pool)return GGML_STATUS_FAILED;
    }
    auto plan=make_plan(graph,threads,state.pool);
    if(plan.work_size) {
        if(state.work.size()<plan.work_size+63)state.work.resize(plan.work_size+63);
        auto address=(reinterpret_cast<uintptr_t>(state.work.data())+63)&~uintptr_t(63);
        plan.work_data=reinterpret_cast<uint8_t *>(address);
    }
    return run(graph,&plan);
}

// components retain the original six-pointer ABI. Gate and up weights must
// be adjacent original packed matrices; gate points to the start of both.
// One matrix-vector operation replaces their two separate projections.
extern "C" int aion_gptoss_moe_finish_joined_active(
    const float * residual, const float * input,
    const void * const * components, const float * gates, int count,
    float * output, int threads, double * elapsed_ms) {
    if (!residual || !input || !components || !gates || !output || !elapsed_ms || threads < 1) return 1;
    if (count < 1 || count > 4) return 6;
    static void * plugin=dlopen("/opt/homebrew/Cellar/ggml/0.23.0/libexec/libggml-cpu-apple_m2_m3.so",RTLD_NOW|RTLD_LOCAL);
    static compute_function compute=plugin ? reinterpret_cast<compute_function>(dlsym(plugin,"ggml_graph_compute_with_ctx")) : nullptr;
    static std::vector<char> memory(256*1024*1024);
    static ggml_context * context=ggml_init({memory.size(),memory.data(),false});
    if (!compute) return 2;
    if (!context) return 3;
    ggml_reset(context);
    constexpr int64_t width=2880;
    const size_t matrix_bytes=ggml_row_size(GGML_TYPE_MXFP4,width)*width;
    auto * x=ggml_new_tensor_1d(context,GGML_TYPE_F32,width);x->data=const_cast<float *>(input);
    auto * r=ggml_new_tensor_1d(context,GGML_TYPE_F32,width);r->data=const_cast<float *>(residual);
    ggml_tensor * combined=nullptr;
    for (int p=0;p<count;++p) {
        const auto * c=components+p*6;
        for(int k=0;k<6;++k) if(!c[k]) return 1;
        if (static_cast<const char *>(c[2])!=static_cast<const char *>(c[0])+matrix_bytes) return 7;
        auto * weights=ggml_new_tensor_2d(context,GGML_TYPE_MXFP4,width,2*width);weights->data=const_cast<void *>(c[0]);
        auto * gate_bias=ggml_new_tensor_1d(context,GGML_TYPE_F32,width);gate_bias->data=const_cast<void *>(c[1]);
        auto * up_bias=ggml_new_tensor_1d(context,GGML_TYPE_F32,width);up_bias->data=const_cast<void *>(c[3]);
        auto * down=ggml_new_tensor_2d(context,GGML_TYPE_MXFP4,width,width);down->data=const_cast<void *>(c[4]);
        auto * down_bias=ggml_new_tensor_1d(context,GGML_TYPE_F32,width);down_bias->data=const_cast<void *>(c[5]);
        auto * projected=ggml_mul_mat(context,weights,x);
        auto * gate=ggml_add(context,ggml_view_1d(context,projected,width,0),gate_bias);
        auto * up=ggml_add(context,ggml_view_1d(context,projected,width,width*sizeof(float)),up_bias);
        auto * hidden=ggml_swiglu_oai(context,gate,up,1.702f,7.0f);
        auto * expert=ggml_add(context,ggml_mul_mat(context,down,hidden),down_bias);
        expert=ggml_scale(context,expert,gates[p]);
        combined=combined?ggml_add(context,combined,expert):expert;
    }
    auto * result=ggml_add(context,r,combined);
    auto * graph=ggml_new_graph_custom(context,GGML_DEFAULT_GRAPH_SIZE,false);
    ggml_build_forward_expand(graph,result);
    auto began=std::chrono::steady_clock::now();
    int status=pooled_compute(plugin,graph,threads);
    *elapsed_ms=std::chrono::duration<double,std::milli>(std::chrono::steady_clock::now()-began).count();
    if(status!=GGML_STATUS_SUCCESS)return 4;
    std::memcpy(output,result->data,width*sizeof(float));
    for(int i=0;i<width;++i)if(!std::isfinite(output[i]))return 5;
    return 0;
}
extern "C" int aion_gptoss_moe_finish_joined(
    const float * r,const float * x,const void * const * c,const float * g,
    float * out,int threads,double * ms) {
    return aion_gptoss_moe_finish_joined_active(r,x,c,g,4,out,threads,ms);
}
