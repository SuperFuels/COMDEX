#import <Foundation/Foundation.h>
#import <Metal/Metal.h>
#include <ggml.h>
#include <ggml-cpu.h>
#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstring>
#include <dlfcn.h>
#include <fstream>
#include <iostream>
#include <vector>

static std::vector<char> read(const char * path,size_t bytes) {
    std::ifstream f(path,std::ios::binary|std::ios::ate);
    if(!f || size_t(f.tellg())!=bytes)throw std::runtime_error("input size mismatch");
    std::vector<char> v(bytes);f.seekg(0);f.read(v.data(),bytes);
    if(!f)throw std::runtime_error("input read failed");return v;
}
int main(int argc,char ** argv) { @autoreleasepool {
    if(argc!=6 && argc!=7){std::cerr<<"INPUT GATE UP GATE_BIAS UP_BIAS [--matched-dot-input]\n";return 2;}
    bool matched=argc==7 && std::strcmp(argv[6],"--matched-dot-input")==0;
    constexpr int W=2880,B=90;constexpr size_t M=size_t(W)*B*17;
    auto input=read(argv[1],W*4),gate=read(argv[2],M),up=read(argv[3],M),gb=read(argv[4],W*4),ub=read(argv[5],W*4);
    size_t scale_histogram[256]={};for(auto * p:{&gate,&up})for(size_t i=0;i<M;i+=17)scale_histogram[uint8_t((*p)[i])]++;
    std::vector<char> arena(32*1024*1024);
    auto * ctx=ggml_init({arena.size(),arena.data(),false});
    void * plugin=dlopen("/opt/homebrew/Cellar/ggml/0.23.0/libexec/libggml-cpu-apple_m2_m3.so",RTLD_NOW|RTLD_LOCAL);
    using Compute=ggml_status(*)(ggml_context*,ggml_cgraph*,int);
    auto compute=reinterpret_cast<Compute>(dlsym(plugin,"ggml_graph_compute_with_ctx"));if(!ctx||!compute)return 3;
    auto * x=ggml_new_tensor_1d(ctx,GGML_TYPE_F32,W);x->data=input.data();
    auto projection=[&](std::vector<char>& weight,std::vector<char>& bias){
        auto * w=ggml_new_tensor_2d(ctx,GGML_TYPE_MXFP4,W,W);w->data=weight.data();
        auto * b=ggml_new_tensor_1d(ctx,GGML_TYPE_F32,W);b->data=bias.data();
        return ggml_add(ctx,ggml_mul_mat(ctx,w,x),b);
    };
    auto * g=projection(gate,gb),*u=projection(up,ub);
    auto * h=ggml_swiglu_oai(ctx,g,u,1.702f,7.f);
    auto * graph=ggml_new_graph_custom(ctx,GGML_DEFAULT_GRAPH_SIZE,false);ggml_build_forward_expand(graph,h);
    if(compute(ctx,graph,6)!=GGML_STATUS_SUCCESS)return 4;
    auto gpu_input=input; // never mutate the authoritative CPU graph's input
    int dot_type=-1;
    if(matched) {
        using Traits=const ggml_type_traits_cpu * (*)(ggml_type);
        auto traits_fn=reinterpret_cast<Traits>(dlsym(plugin,"ggml_get_type_traits_cpu"));
        if(!traits_fn)return 9;
        auto * weight_traits=traits_fn(GGML_TYPE_MXFP4);dot_type=weight_traits->vec_dot_type;
        auto * dot_traits=traits_fn(weight_traits->vec_dot_type);
        std::vector<char> quantized(ggml_row_size(weight_traits->vec_dot_type,W));
        dot_traits->from_float(reinterpret_cast<float *>(input.data()),quantized.data(),W);
        ggml_get_type_traits(weight_traits->vec_dot_type)->to_float(quantized.data(),reinterpret_cast<float *>(gpu_input.data()),W);
    }
    NSString * source=@R"METAL(
#include <metal_stdlib>
using namespace metal;
kernel void fused(device const float * x [[buffer(0)]],device const uchar * gw [[buffer(1)]],device const uchar * uw [[buffer(2)]],device const float * gb [[buffer(3)]],device const float * ub [[buffer(4)]],device float * out [[buffer(5)]],uint group [[threadgroup_position_in_grid]],uint lane [[thread_index_in_simdgroup]]) {
    const float grid[16]={0.f,.5f,1.f,1.5f,2.f,3.f,4.f,6.f,0.f,-.5f,-1.f,-1.5f,-2.f,-3.f,-4.f,-6.f};
    float sg=0.f,su=0.f;
    for(uint block=lane;block<90;block+=32) {
        uint offset=(group*90+block)*17;
        float gs=ldexp(1.f,int(gw[offset])-127),us=ldexp(1.f,int(uw[offset])-127);
        for(uint k=0;k<32;k++) {
            uchar gc=gw[offset+1+k%16],uc=uw[offset+1+k%16];
            uint gi=k<16?gc&15:gc>>4,ui=k<16?uc&15:uc>>4;
            sg+=x[block*32+k]*(grid[gi]*gs);su+=x[block*32+k]*(grid[ui]*us);
        }
    }
    float g=simd_sum(sg)+gb[group],u=simd_sum(su)+ub[group];
    if(lane==0) {
        out[group]=g;out[2880+group]=u;
        float swish=min(g,7.f),linear=clamp(u,-7.f,7.f);
        out[5760+group]=(swish/(1.f+exp(-1.702f*swish)))*(linear+1.f);
    }
}
)METAL";
    id<MTLDevice> device=MTLCreateSystemDefaultDevice();if(!device)return 5;
    NSError * error=nil;MTLCompileOptions * options=[MTLCompileOptions new];options.fastMathEnabled=NO;
    id<MTLLibrary> lib=[device newLibraryWithSource:source options:options error:&error];
    if(!lib){std::cerr<<error.description.UTF8String;return 6;}
    auto pipeline=[device newComputePipelineStateWithFunction:[lib newFunctionWithName:@"fused"] error:&error];if(!pipeline)return 7;
    id<MTLBuffer> buffers[6];int i=0;for(auto * data:{&gpu_input,&gate,&up,&gb,&ub})buffers[i++]=[device newBufferWithBytes:data->data() length:data->size() options:MTLResourceStorageModeShared];
    buffers[5]=[device newBufferWithLength:W*12 options:MTLResourceStorageModeShared];
    auto queue=[device newCommandQueue];auto command=[queue commandBuffer];auto encoder=[command computeCommandEncoder];
    [encoder setComputePipelineState:pipeline];for(i=0;i<6;i++)[encoder setBuffer:buffers[i] offset:0 atIndex:i];
    [encoder dispatchThreadgroups:MTLSizeMake(W,1,1) threadsPerThreadgroup:MTLSizeMake(32,1,1)];
    [encoder endEncoding];[command commit];[command waitUntilCompleted];if(command.status!=MTLCommandBufferStatusCompleted)return 8;
    auto * actual=static_cast<float *>(buffers[5].contents);
    std::cout<<"{\"matched_dot_input\":"<<(matched?"true":"false")<<",\"dot_input_type\":"<<dot_type<<",\"scale_zero_blocks\":"<<scale_histogram[0]<<",\"scale_one_blocks\":"<<scale_histogram[1]<<",\"total_blocks\":"<<2*W*B<<",\"stages\":[";
    int stage=0;for(auto * t:{g,u,h}) {
        auto * expected=static_cast<float *>(t->data);double err=0,norm=0,maxerr=0;int different=0;
        for(i=0;i<W;i++){double delta=double(actual[stage*W+i])-expected[i];err+=delta*delta;norm+=double(expected[i])*expected[i];maxerr=std::max(maxerr,std::abs(delta));different+=memcmp(actual+stage*W+i,expected+i,4)!=0;}
        if(stage)std::cout<<",";std::cout<<"{\"bitwise_mismatches\":"<<different<<",\"relative_l2\":"<<sqrt(err/norm)<<",\"max_abs\":"<<maxerr<<"}";stage++;
    }
    std::cout<<"],\"claim_boundary\":\"Single original expert gate/up fusion numerical gate only; no timing or model substitution\"}\n";
    ggml_free(ctx);return 0;
}}
