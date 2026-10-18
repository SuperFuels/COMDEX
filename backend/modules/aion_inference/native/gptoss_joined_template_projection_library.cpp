#include <chrono>
#include <cmath>
#include <cstring>
#include <dlfcn.h>
#include <vector>
#include <array>
#include <mutex>
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
    // One graph per active count. Bind every external buffer anew on each call;
    // graph reuse never extends the lifetime of caller-owned expert weights.
    struct Template {
        std::vector<char> memory;
        ggml_context * context=nullptr;
        ggml_tensor * x=nullptr,*r=nullptr,*result=nullptr;
        ggml_cgraph * graph=nullptr;
        std::array<std::array<ggml_tensor *,6>,4> components{};
        std::array<ggml_tensor *,4> scaled{};
        ~Template(){if(context)ggml_free(context);}
    };
    static std::array<Template,4> templates;
    static std::mutex mutex;
    std::lock_guard<std::mutex> guard(mutex);
    if (!compute) return 2;
    constexpr int64_t width=2880;
    const size_t matrix_bytes=ggml_row_size(GGML_TYPE_MXFP4,width)*width;
    for(int p=0;p<count;++p) {
        const auto * c=components+p*6;
        for(int k=0;k<6;++k)if(!c[k])return 1;
        if(static_cast<const char *>(c[2])!=static_cast<const char *>(c[0])+matrix_bytes)return 7;
    }
    auto & t=templates[count-1];
    if(!t.context) {
        t.memory.resize(64*1024*1024);
        t.context=ggml_init({t.memory.size(),t.memory.data(),false});
        if(!t.context)return 3;
        auto * context=t.context;
        t.x=ggml_new_tensor_1d(context,GGML_TYPE_F32,width);
        t.r=ggml_new_tensor_1d(context,GGML_TYPE_F32,width);
        ggml_tensor * combined=nullptr;
        for(int p=0;p<count;++p) {
            auto & c=t.components[p];
            c[0]=ggml_new_tensor_2d(context,GGML_TYPE_MXFP4,width,2*width);
            c[1]=ggml_new_tensor_1d(context,GGML_TYPE_F32,width);
            c[3]=ggml_new_tensor_1d(context,GGML_TYPE_F32,width);
            c[4]=ggml_new_tensor_2d(context,GGML_TYPE_MXFP4,width,width);
            c[5]=ggml_new_tensor_1d(context,GGML_TYPE_F32,width);
            auto * projected=ggml_mul_mat(context,c[0],t.x);
            auto * gate=ggml_add(context,ggml_view_1d(context,projected,width,0),c[1]);
            auto * up=ggml_add(context,ggml_view_1d(context,projected,width,width*sizeof(float)),c[3]);
            auto * hidden=ggml_swiglu_oai(context,gate,up,1.702f,7.0f);
            auto * expert=ggml_add(context,ggml_mul_mat(context,c[4],hidden),c[5]);
            t.scaled[p]=ggml_scale(context,expert,1.0f);
            combined=combined?ggml_add(context,combined,t.scaled[p]):t.scaled[p];
        }
        t.result=ggml_add(context,t.r,combined);
        t.graph=ggml_new_graph_custom(context,GGML_DEFAULT_GRAPH_SIZE,false);
        ggml_build_forward_expand(t.graph,t.result);
    }
    t.x->data=const_cast<float *>(input);t.r->data=const_cast<float *>(residual);
    for(int p=0;p<count;++p) {
        for(int k : {0,1,3,4,5})t.components[p][k]->data=const_cast<void *>(components[p*6+k]);
        std::memcpy(t.scaled[p]->op_params,gates+p,sizeof(float));
    }
    auto * graph=t.graph;auto * result=t.result;
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
