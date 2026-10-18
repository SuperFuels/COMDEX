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
    if(argc<6 || argc>9){std::cerr<<"INPUT GATE UP GATE_BIAS UP_BIAS [--matched-dot-input] [--timing] [--integer-dot|--tiled-dot]\n";return 2;}
    bool matched=false,timing=false,integer_dot=false,tiled_dot=false;
    for(int arg=6;arg<argc;arg++){if(std::strcmp(argv[arg],"--matched-dot-input")==0)matched=true;else if(std::strcmp(argv[arg],"--timing")==0)timing=true;else if(std::strcmp(argv[arg],"--integer-dot")==0)integer_dot=true;else if(std::strcmp(argv[arg],"--tiled-dot")==0){integer_dot=true;tiled_dot=true;}else return 2;}
    if(integer_dot && !matched)return 2;
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
    std::vector<char> packed_input;
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
        if(integer_dot) {
            if(dot_type!=GGML_TYPE_Q8_0 || ggml_blck_size(GGML_TYPE_Q8_0)!=32 || ggml_type_size(GGML_TYPE_Q8_0)!=34)return 11;
            packed_input=quantized;
            for(int block=0;block<B;block++) {
                ggml_fp16_t scale;std::memcpy(&scale,quantized.data()+block*34,2);
                for(int k=0;k<32;k++) {
                    float decoded=ggml_fp16_to_fp32(scale)*int(static_cast<int8_t>(quantized[block*34+2+k]));
                    if(std::memcmp(&decoded,gpu_input.data()+(block*32+k)*4,4)!=0)return 12;
                }
            }
        }
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
kernel void fused_integer(device const uchar * x [[buffer(0)]],device const uchar * gw [[buffer(1)]],device const uchar * uw [[buffer(2)]],device const float * gb [[buffer(3)]],device const float * ub [[buffer(4)]],device float * out [[buffer(5)]],uint group [[threadgroup_position_in_grid]],uint lane [[thread_index_in_simdgroup]]) {
    const int grid[16]={0,1,2,3,4,6,8,12,0,-1,-2,-3,-4,-6,-8,-12};
    float sg=0.f,su=0.f;
    for(uint block=lane;block<90;block+=32) {
        uint offset=(group*90+block)*17;
        int dg=0,du=0;
        for(uint k=0;k<32;k++) {
            uchar gc=gw[offset+1+k%16],uc=uw[offset+1+k%16];
            uint gi=k<16?gc&15:gc>>4,ui=k<16?uc&15:uc>>4;
            int activation=int(as_type<char>(x[block*34+2+k]));
            dg+=activation*grid[gi];du+=activation*grid[ui];
        }
        float xs=float(as_type<half>(*reinterpret_cast<device const ushort *>(x+block*34)))*.5f;
        sg+=float(dg)*(ldexp(1.f,int(gw[offset])-127)*xs);
        su+=float(du)*(ldexp(1.f,int(uw[offset])-127)*xs);
    }
    float g=simd_sum(sg)+gb[group],u=simd_sum(su)+ub[group];
    if(lane==0){out[group]=g;out[2880+group]=u;float swish=min(g,7.f),linear=clamp(u,-7.f,7.f);out[5760+group]=(swish/(1.f+exp(-1.702f*swish)))*(linear+1.f);}
}
int4 unpack4(uint4 code) {
    int4 magnitude=int4(code&7);
    int4 large=(2+(magnitude&1))<<max((magnitude>>1)-1,0);
    int4 value=select(large,magnitude,magnitude<4);
    return select(value,-value,(code&8)!=0);
}
uchar4 load4(device const uchar * ptr) { return uchar4(ptr[0],ptr[1],ptr[2],ptr[3]); }
int sum4(int4 x) { return x.x+x.y+x.z+x.w; }
kernel void fused_tiled(device const uchar * x [[buffer(0)]],device const uchar * gw [[buffer(1)]],device const uchar * uw [[buffer(2)]],device const float * gb [[buffer(3)]],device const float * ub [[buffer(4)]],device float * out [[buffer(5)]],uint group [[threadgroup_position_in_grid]],uint lane [[thread_index_in_simdgroup]]) {
    float sg=0.f,su=0.f;
    uint k=(lane%4)*4;
    for(uint block=lane/4;block<90;block+=8) {
        uint offset=(group*90+block)*17;
        uint4 gc=uint4(load4(gw+offset+1+k)),uc=uint4(load4(uw+offset+1+k));
        int4 low=int4(as_type<char4>(load4(x+block*34+2+k)));
        int4 high=int4(as_type<char4>(load4(x+block*34+18+k)));
        int dg=sum4(low*unpack4(gc&15)+high*unpack4(gc>>4));
        int du=sum4(low*unpack4(uc&15)+high*unpack4(uc>>4));
        float xs=float(as_type<half>(*reinterpret_cast<device const ushort *>(x+block*34)))*.5f;
        sg+=float(dg)*(ldexp(1.f,int(gw[offset])-127)*xs);
        su+=float(du)*(ldexp(1.f,int(uw[offset])-127)*xs);
    }
    float g=simd_sum(sg)+gb[group],u=simd_sum(su)+ub[group];
    if(lane==0){out[group]=g;out[2880+group]=u;float swish=min(g,7.f),linear=clamp(u,-7.f,7.f);out[5760+group]=(swish/(1.f+exp(-1.702f*swish)))*(linear+1.f);}
}
)METAL";
    id<MTLDevice> device=MTLCreateSystemDefaultDevice();if(!device)return 5;
    NSError * error=nil;MTLCompileOptions * options=[MTLCompileOptions new];options.fastMathEnabled=NO;
    id<MTLLibrary> lib=[device newLibraryWithSource:source options:options error:&error];
    if(!lib){std::cerr<<error.description.UTF8String;return 6;}
    auto pipeline=[device newComputePipelineStateWithFunction:[lib newFunctionWithName:tiled_dot?@"fused_tiled":integer_dot?@"fused_integer":@"fused"] error:&error];if(!pipeline)return 7;
    auto * device_input=integer_dot?&packed_input:&gpu_input;
    id<MTLBuffer> buffers[6];int i=0;for(auto * data:{device_input,&gate,&up,&gb,&ub})buffers[i++]=[device newBufferWithBytes:data->data() length:data->size() options:MTLResourceStorageModeShared];
    buffers[5]=[device newBufferWithLength:W*12 options:MTLResourceStorageModeShared];
    auto queue=[device newCommandQueue];auto command=[queue commandBuffer];auto encoder=[command computeCommandEncoder];
    [encoder setComputePipelineState:pipeline];for(i=0;i<6;i++)[encoder setBuffer:buffers[i] offset:0 atIndex:i];
    [encoder dispatchThreadgroups:MTLSizeMake(W,1,1) threadsPerThreadgroup:MTLSizeMake(32,1,1)];
    [encoder endEncoding];[command commit];[command waitUntilCompleted];if(command.status!=MTLCommandBufferStatusCompleted)return 8;
    std::vector<char> first_output(W*12);std::memcpy(first_output.data(),buffers[5].contents,W*12);
    auto repeat_command=[queue commandBuffer];auto repeat_encoder=[repeat_command computeCommandEncoder];
    [repeat_encoder setComputePipelineState:pipeline];for(i=0;i<6;i++)[repeat_encoder setBuffer:buffers[i] offset:0 atIndex:i];
    [repeat_encoder dispatchThreadgroups:MTLSizeMake(W,1,1) threadsPerThreadgroup:MTLSizeMake(32,1,1)];
    [repeat_encoder endEncoding];[repeat_command commit];[repeat_command waitUntilCompleted];if(repeat_command.status!=MTLCommandBufferStatusCompleted)return 8;
    bool repeat_equal=std::memcmp(first_output.data(),buffers[5].contents,W*12)==0;
    std::vector<double> cpu_samples,gpu_samples;
    std::vector<double> gpu_device_samples,conversion_samples,host_encode_samples,submit_wait_samples;
    if(timing) {
        if(!matched)return 10;
        using Traits=const ggml_type_traits_cpu * (*)(ggml_type);
        auto traits_fn=reinterpret_cast<Traits>(dlsym(plugin,"ggml_get_type_traits_cpu"));
        auto * dot_traits=traits_fn(ggml_type(dot_type));
        std::vector<char> quantized(ggml_row_size(ggml_type(dot_type),W)),readback(W*12);
        for(int round=0;round<28;round++)for(int mode:{0,1,1,0}) {
            auto begin=std::chrono::steady_clock::now();
            if(mode==0) {
                if(compute(ctx,graph,6)!=GGML_STATUS_SUCCESS)return 4;
                std::memcpy(readback.data(),g->data,W*4);std::memcpy(readback.data()+W*4,u->data,W*4);std::memcpy(readback.data()+W*8,h->data,W*4);
            } else {
                dot_traits->from_float(reinterpret_cast<float *>(input.data()),quantized.data(),W);
                if(integer_dot)std::memcpy(buffers[0].contents,quantized.data(),quantized.size());
                else ggml_get_type_traits(ggml_type(dot_type))->to_float(quantized.data(),static_cast<float *>(buffers[0].contents),W);
                auto converted=std::chrono::steady_clock::now();
                auto cmd=[queue commandBuffer];auto enc=[cmd computeCommandEncoder];
                [enc setComputePipelineState:pipeline];for(int k=0;k<6;k++)[enc setBuffer:buffers[k] offset:0 atIndex:k];
                [enc dispatchThreadgroups:MTLSizeMake(W,1,1) threadsPerThreadgroup:MTLSizeMake(32,1,1)];
                [enc endEncoding];auto encoded=std::chrono::steady_clock::now();[cmd commit];[cmd waitUntilCompleted];if(cmd.status!=MTLCommandBufferStatusCompleted)return 8;
                auto completed=std::chrono::steady_clock::now();
                if(round>=4) {
                    conversion_samples.push_back(std::chrono::duration<double,std::milli>(converted-begin).count());
                    host_encode_samples.push_back(std::chrono::duration<double,std::milli>(encoded-converted).count());
                    submit_wait_samples.push_back(std::chrono::duration<double,std::milli>(completed-encoded).count());
                    if(cmd.GPUEndTime>cmd.GPUStartTime)gpu_device_samples.push_back((cmd.GPUEndTime-cmd.GPUStartTime)*1000);
                }
                std::memcpy(readback.data(),buffers[5].contents,W*12);
                repeat_equal &= std::memcmp(readback.data(),first_output.data(),W*12)==0;
            }
            double ms=std::chrono::duration<double,std::milli>(std::chrono::steady_clock::now()-begin).count();
            if(round>=4)(mode==0?cpu_samples:gpu_samples).push_back(ms);
        }
        std::sort(cpu_samples.begin(),cpu_samples.end());std::sort(gpu_samples.begin(),gpu_samples.end());
        for(auto * samples:{&gpu_device_samples,&conversion_samples,&host_encode_samples,&submit_wait_samples})std::sort(samples->begin(),samples->end());
    }
    auto * actual=static_cast<float *>(buffers[5].contents);
    std::cout<<"{\"tiled_dot\":"<<(tiled_dot?"true":"false")<<",\"integer_dot\":"<<(integer_dot?"true":"false")<<",\"gpu_input_bytes\":"<<device_input->size()<<",\"gpu_bitwise_repeatable\":"<<(repeat_equal?"true":"false")<<",\"matched_dot_input\":"<<(matched?"true":"false")<<",\"dot_input_type\":"<<dot_type<<",\"scale_zero_blocks\":"<<scale_histogram[0]<<",\"scale_one_blocks\":"<<scale_histogram[1]<<",\"total_blocks\":"<<2*W*B<<",\"stages\":[";
    int stage=0;for(auto * t:{g,u,h}) {
        auto * expected=static_cast<float *>(t->data);double err=0,norm=0,maxerr=0;int different=0;
        for(i=0;i<W;i++){double delta=double(actual[stage*W+i])-expected[i];err+=delta*delta;norm+=double(expected[i])*expected[i];maxerr=std::max(maxerr,std::abs(delta));different+=memcmp(actual+stage*W+i,expected+i,4)!=0;}
        if(stage)std::cout<<",";std::cout<<"{\"bitwise_mismatches\":"<<different<<",\"relative_l2\":"<<sqrt(err/norm)<<",\"max_abs\":"<<maxerr<<"}";stage++;
    }
    std::cout<<"]";
    if(timing)std::cout<<",\"timing\":{\"samples_per_mode\":48,\"cpu_p50_ms\":"<<(cpu_samples[23]+cpu_samples[24])*.5<<",\"gpu_charged_p50_ms\":"<<(gpu_samples[23]+gpu_samples[24])*.5<<",\"cpu_p95_ms\":"<<cpu_samples[44]<<",\"gpu_charged_p95_ms\":"<<gpu_samples[44]<<",\"all_gpu_samples_bitwise_repeatable\":"<<(repeat_equal?"true":"false")<<",\"gpu_buffer_bytes\":"<<2*M+W*20+device_input->size()<<",\"cpu_context_arena_bytes\":"<<arena.size()<<"}";
    if(timing) {
        auto median=[](const std::vector<double>& s){return s.empty()?-1.:(s[(s.size()-1)/2]+s[s.size()/2])*.5;};
        std::cout<<",\"diagnostic_phases\":{\"gpu_timestamp_samples\":"<<gpu_device_samples.size()<<",\"gpu_device_p50_ms\":"<<median(gpu_device_samples)<<",\"conversion_p50_ms\":"<<median(conversion_samples)<<",\"host_encoding_p50_ms\":"<<median(host_encode_samples)<<",\"submit_wait_p50_ms\":"<<median(submit_wait_samples)<<",\"boundary\":\"Device timestamp overlaps host wait; independent medians are not additive\"}";
    }
    std::cout<<",\"claim_boundary\":\"Single original expert gate/up fusion only; CPU reference uses installed with-ctx worker dispatch; no model substitution or generation speed claim\"}\n";
    ggml_free(ctx);return 0;
}}
