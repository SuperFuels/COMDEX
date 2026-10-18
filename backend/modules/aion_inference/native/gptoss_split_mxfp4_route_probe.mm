#import <Foundation/Foundation.h>
#import <Metal/Metal.h>
#include <algorithm>
#include <chrono>
#include <fstream>
#include <iostream>
#include <sstream>
#include <string>
#include <vector>
#include <cstdlib>

static bool read_file(const std::string & path, std::vector<char> & out) {
    std::ifstream f(path, std::ios::binary | std::ios::ate); if (!f) return false;
    out.resize(size_t(f.tellg())); f.seekg(0); f.read(out.data(), std::streamsize(out.size())); return f.good();
}
static std::vector<float> csv(const char * value) {
    std::vector<float> out; std::stringstream s(value); std::string item;
    while (std::getline(s,item,',')) out.push_back(std::stof(item)); return out;
}
static void split_weight(const std::vector<char> & packed, std::vector<char> & values,
                         std::vector<uint8_t> & scales) {
    const size_t blocks=packed.size()/17, value_start=values.size(), scale_start=scales.size();
    values.resize(value_start+blocks*16); scales.resize(scale_start+blocks);
    for(size_t block=0;block<blocks;++block){
        scales[scale_start+block]=uint8_t(packed[block*17]);
        const auto *src=reinterpret_cast<const uint8_t*>(packed.data()+block*17+1);
        auto *dst=reinterpret_cast<uint8_t*>(values.data()+value_start+block*16);
        uint8_t unpacked[32];
        for(int i=0;i<16;++i){unpacked[i]=src[i]&15;unpacked[i+16]=src[i]>>4;}
        for(int i=0;i<16;++i)dst[i]=unpacked[2*i]|(unpacked[2*i+1]<<4);
    }
}
int main(int argc,char **argv){
    if(argc!=6){std::cerr<<"usage: probe METAL COMPONENT_DIR GATES INPUT OUTPUT\n";return 2;}
    constexpr uint32_t width=2880, blocks=90; const size_t weight_bytes=size_t(width)*blocks*17;
    auto gates=csv(argv[3]); if(gates.size()!=4)return 3;
    std::vector<char> input; if(!read_file(argv[4],input)||input.size()!=width*4)return 4;
    std::vector<char> gu_values,down_values,gu_biases,down_biases;
    std::vector<uint8_t> gu_scales,down_scales;
    auto begin_split=std::chrono::steady_clock::now();
    for(int expert=0;expert<4;++expert){
        for(const char *projection:{"gate","up"}){
            std::vector<char>w,b;std::string p=std::string(argv[2])+"/"+std::to_string(expert)+"-"+projection;
            if(!read_file(p+"-weight.bin",w)||w.size()!=weight_bytes||!read_file(p+"-bias.bin",b)||b.size()!=width*4)return 5;
            split_weight(w,gu_values,gu_scales);gu_biases.insert(gu_biases.end(),b.begin(),b.end());
        }
    }
    for(int expert=0;expert<4;++expert){
        std::vector<char>w,b;std::string p=std::string(argv[2])+"/"+std::to_string(expert)+"-down";
        if(!read_file(p+"-weight.bin",w)||w.size()!=weight_bytes||!read_file(p+"-bias.bin",b)||b.size()!=width*4)return 6;
        split_weight(w,down_values,down_scales);down_biases.insert(down_biases.end(),b.begin(),b.end());
    }
    const double split_ms=std::chrono::duration<double,std::milli>(std::chrono::steady_clock::now()-begin_split).count();
    @autoreleasepool{
        id<MTLDevice>d=MTLCreateSystemDefaultDevice();NSError*e=nil;
        NSString*s=[NSString stringWithContentsOfFile:[NSString stringWithUTF8String:argv[1]] encoding:NSUTF8StringEncoding error:&e];
        MTLCompileOptions*o=[MTLCompileOptions new];o.fastMathEnabled=NO;
        id<MTLLibrary>l=[d newLibraryWithSource:s options:o error:&e];if(!l){std::cerr<<e.localizedDescription.UTF8String;return 7;}
        auto pipe=[&](NSString*n){return[d newComputePipelineStateWithFunction:[l newFunctionWithName:n] error:&e];};
        id<MTLComputePipelineState>pgu=pipe(@"route_gate_up"),psw=pipe(@"route_swiglu"),pdn=pipe(@"route_down"),pcm=pipe(@"route_combine");if(!pgu||!psw||!pdn||!pcm)return 8;
        struct Args{uint32_t blocks_per_row,rows;}args{blocks,width};
        auto buf=[&](const void*p,size_t n){return[d newBufferWithBytes:p length:n options:MTLResourceStorageModeShared];};
        id<MTLBuffer>ba=buf(&args,sizeof(args)),bi=buf(input.data(),input.size()),bg=buf(gates.data(),16);
        id<MTLBuffer>bgv=buf(gu_values.data(),gu_values.size()),bgs=buf(gu_scales.data(),gu_scales.size()),bgb=buf(gu_biases.data(),gu_biases.size());
        id<MTLBuffer>bdv=buf(down_values.data(),down_values.size()),bds=buf(down_scales.data(),down_scales.size()),bdb=buf(down_biases.data(),down_biases.size());
        id<MTLBuffer>projected=[d newBufferWithLength:8*width*4 options:MTLResourceStorageModeShared],hidden=[d newBufferWithLength:4*width*4 options:MTLResourceStorageModeShared],expertout=[d newBufferWithLength:4*width*4 options:MTLResourceStorageModeShared],out=[d newBufferWithLength:width*4 options:MTLResourceStorageModeShared];
        const int thrash_mib=std::getenv("AION_CPU_CACHE_THRASH_MIB")?std::stoi(std::getenv("AION_CPU_CACHE_THRASH_MIB")):0;
        std::vector<unsigned char>thrash(size_t(thrash_mib)*1024*1024);volatile unsigned long long thrash_sum=0;
        id<MTLCommandQueue>q=[d newCommandQueue];std::vector<double>times;
        for(int rep=0;rep<21;++rep){
            for(size_t offset=0;offset<thrash.size();offset+=64){thrash[offset]=static_cast<unsigned char>(thrash[offset]+rep+1);thrash_sum+=thrash[offset];}
            auto start=std::chrono::steady_clock::now();id<MTLCommandBuffer>c=[q commandBuffer];
            id<MTLComputeCommandEncoder>x=[c computeCommandEncoder];[x setComputePipelineState:pgu];[x setBuffer:ba offset:0 atIndex:0];[x setBuffer:bi offset:0 atIndex:1];[x setBuffer:bgv offset:0 atIndex:2];[x setBuffer:bgs offset:0 atIndex:3];[x setBuffer:bgb offset:0 atIndex:4];[x setBuffer:projected offset:0 atIndex:5];NSUInteger th=std::min<NSUInteger>(1024,pgu.maxTotalThreadsPerThreadgroup),sg=th/pgu.threadExecutionWidth;[x dispatchThreadgroups:MTLSizeMake((width+sg-1)/sg,8,1) threadsPerThreadgroup:MTLSizeMake(th,1,1)];[x endEncoding];
            x=[c computeCommandEncoder];[x setComputePipelineState:psw];[x setBuffer:projected offset:0 atIndex:0];[x setBuffer:hidden offset:0 atIndex:1];[x dispatchThreads:MTLSizeMake(4*width,1,1) threadsPerThreadgroup:MTLSizeMake(std::min<NSUInteger>(256,psw.maxTotalThreadsPerThreadgroup),1,1)];[x endEncoding];
            x=[c computeCommandEncoder];[x setComputePipelineState:pdn];[x setBuffer:ba offset:0 atIndex:0];[x setBuffer:hidden offset:0 atIndex:1];[x setBuffer:bdv offset:0 atIndex:2];[x setBuffer:bds offset:0 atIndex:3];[x setBuffer:bdb offset:0 atIndex:4];[x setBuffer:expertout offset:0 atIndex:5];th=std::min<NSUInteger>(1024,pdn.maxTotalThreadsPerThreadgroup);sg=th/pdn.threadExecutionWidth;[x dispatchThreadgroups:MTLSizeMake((width+sg-1)/sg,4,1) threadsPerThreadgroup:MTLSizeMake(th,1,1)];[x endEncoding];
            x=[c computeCommandEncoder];[x setComputePipelineState:pcm];[x setBuffer:expertout offset:0 atIndex:0];[x setBuffer:bg offset:0 atIndex:1];[x setBuffer:out offset:0 atIndex:2];[x dispatchThreads:MTLSizeMake(width,1,1) threadsPerThreadgroup:MTLSizeMake(std::min<NSUInteger>(256,pcm.maxTotalThreadsPerThreadgroup),1,1)];[x endEncoding];[c commit];[c waitUntilCompleted];times.push_back(std::chrono::duration<double,std::milli>(std::chrono::steady_clock::now()-start).count());}
        std::ofstream f(argv[5],std::ios::binary|std::ios::trunc);f.write(static_cast<const char*>(out.contents),width*4);if(!f.good())return 9;
        std::sort(times.begin()+1,times.end());std::cout<<"{\"status\":\"PASSED\",\"first_ms\":"<<times[0]<<",\"warm_p50_ms\":"<<(times[10]+times[11])*.5<<",\"warm_p95_ms\":"<<times[20]<<",\"split_ms\":"<<split_ms<<",\"cache_thrash_mib\":"<<thrash_mib<<",\"cache_thrash_checksum\":"<<thrash_sum<<",\"packed_value_bytes\":"<<gu_values.size()+down_values.size()<<",\"scale_bytes\":"<<gu_scales.size()+down_scales.size()<<"}\n";
    }return 0;
}
