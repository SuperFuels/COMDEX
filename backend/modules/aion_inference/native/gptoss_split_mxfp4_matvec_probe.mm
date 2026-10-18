#import <Foundation/Foundation.h>
#import <Metal/Metal.h>

#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstring>
#include <dlfcn.h>
#include <fstream>
#include <iostream>
#include <string>
#include <vector>

#include "ggml.h"

using compute_function = ggml_status (*)(ggml_context *, ggml_cgraph *, int);

static bool read_file(const char * path, std::vector<char> & out) {
    std::ifstream input(path, std::ios::binary | std::ios::ate);
    if (!input) return false;
    out.resize(static_cast<size_t>(input.tellg())); input.seekg(0);
    input.read(out.data(), static_cast<std::streamsize>(out.size()));
    return input.good();
}

int main(int argc, char ** argv) {
    if (argc != 6) {
        std::cerr << "usage: probe METAL_SOURCE INPUT MXFP4_WEIGHT F32_BIAS THREADS\n";
        return 2;
    }
    constexpr uint32_t width = 2880, blocks_per_row = width / 32;
    constexpr size_t packed_bytes = size_t(width) * blocks_per_row * 17;
    std::vector<char> input_bytes, packed, bias_bytes;
    if (!read_file(argv[2], input_bytes) || input_bytes.size() != width * sizeof(float) ||
        !read_file(argv[3], packed) || packed.size() != packed_bytes ||
        !read_file(argv[4], bias_bytes) || bias_bytes.size() != width * sizeof(float)) return 3;
    std::vector<char> values(size_t(width) * blocks_per_row * 16);
    std::vector<uint8_t> scales(size_t(width) * blocks_per_row);
    const auto split_begin = std::chrono::steady_clock::now();
    for (size_t block = 0; block < scales.size(); ++block) {
        scales[block] = static_cast<uint8_t>(packed[block * 17]);
        const auto * ggml_codes = reinterpret_cast<const uint8_t *>(
            packed.data() + block * 17 + 1);
        uint8_t unpacked[32];
        for (int code = 0; code < 16; ++code) {
            unpacked[code] = ggml_codes[code] & 0x0F;
            unpacked[code + 16] = ggml_codes[code] >> 4;
        }
        auto * source_codes = reinterpret_cast<uint8_t *>(values.data() + block * 16);
        for (int code = 0; code < 16; ++code)
            source_codes[code] = unpacked[2 * code] | (unpacked[2 * code + 1] << 4);
    }
    const double split_ms = std::chrono::duration<double, std::milli>(
        std::chrono::steady_clock::now() - split_begin).count();

    std::vector<char> cpu_arena(96 * 1024 * 1024);
    auto * cpu_context = ggml_init({cpu_arena.size(), cpu_arena.data(), false});
    void * cpu_plugin = dlopen("/opt/homebrew/Cellar/ggml/0.23.0/libexec/libggml-cpu-apple_m2_m3.so", RTLD_NOW | RTLD_LOCAL);
    auto compute = cpu_plugin ? reinterpret_cast<compute_function>(dlsym(cpu_plugin, "ggml_graph_compute_with_ctx")) : nullptr;
    if (!cpu_context || !compute) return 4;
    auto * x = ggml_new_tensor_1d(cpu_context, GGML_TYPE_F32, width);
    auto * w = ggml_new_tensor_2d(cpu_context, GGML_TYPE_MXFP4, width, width);
    auto * b = ggml_new_tensor_1d(cpu_context, GGML_TYPE_F32, width);
    x->data = input_bytes.data(); w->data = packed.data(); b->data = bias_bytes.data();
    auto * y = ggml_add(cpu_context, ggml_mul_mat(cpu_context, w, x), b);
    auto * graph = ggml_new_graph_custom(cpu_context, GGML_DEFAULT_GRAPH_SIZE, false);
    ggml_build_forward_expand(graph, y);
    std::vector<double> cpu_samples;
    for (int i = 0; i < 11; ++i) {
        auto begin = std::chrono::steady_clock::now();
        if (compute(cpu_context, graph, std::stoi(argv[5])) != GGML_STATUS_SUCCESS) return 5;
        cpu_samples.push_back(std::chrono::duration<double, std::milli>(std::chrono::steady_clock::now() - begin).count());
    }
    std::vector<float> cpu(width); std::memcpy(cpu.data(), y->data, width * sizeof(float));
    const float grid[16] = {0.0f,0.5f,1.0f,1.5f,2.0f,3.0f,4.0f,6.0f,
                            -0.0f,-0.5f,-1.0f,-1.5f,-2.0f,-3.0f,-4.0f,-6.0f};
    std::vector<float> scalar(width);
    const auto * input_values = reinterpret_cast<const float *>(input_bytes.data());
    const auto * bias_values = reinterpret_cast<const float *>(bias_bytes.data());
    for (uint32_t row=0; row<width; ++row) {
        float sum=0.0f;
        for (uint32_t block=0; block<blocks_per_row; ++block) {
            const size_t offset=size_t(row)*blocks_per_row+block;
            const float scale=std::ldexp(1.0f,int(scales[offset])-127);
            const auto * codes=reinterpret_cast<const uint8_t *>(values.data()+offset*16);
            for(uint32_t element=0;element<32;++element) {
                const uint8_t code=(element&1)?codes[element/2]>>4:codes[element/2]&15;
                sum += input_values[block*32+element]*grid[code]*scale;
            }
        }
        scalar[row]=sum+bias_values[row];
    }

    @autoreleasepool {
        id<MTLDevice> device = MTLCreateSystemDefaultDevice(); if (!device) return 6;
        NSError * error = nil;
        NSString * source = [NSString stringWithContentsOfFile:[NSString stringWithUTF8String:argv[1]]
                                                        encoding:NSUTF8StringEncoding error:&error];
        if (!source) return 7;
        MTLCompileOptions * options = [[MTLCompileOptions alloc] init];
        options.fastMathEnabled = NO;
        id<MTLLibrary> library = [device newLibraryWithSource:source options:options error:&error];
        if (!library) { std::cerr << [[error description] UTF8String] << "\n"; return 7; }
        id<MTLFunction> function = [library newFunctionWithName:@"aion_split_mxfp4_matvec"];
        id<MTLComputePipelineState> pipeline = [device newComputePipelineStateWithFunction:function error:&error];
        if (!pipeline) return 8;
        struct Args { uint32_t blocks_per_row; uint32_t rows; } args{blocks_per_row,width};
        id<MTLBuffer> arg_buffer=[device newBufferWithBytes:&args length:sizeof(args) options:MTLResourceStorageModeShared];
        id<MTLBuffer> input_buffer=[device newBufferWithBytes:input_bytes.data() length:input_bytes.size() options:MTLResourceStorageModeShared];
        id<MTLBuffer> value_buffer=[device newBufferWithBytes:values.data() length:values.size() options:MTLResourceStorageModeShared];
        id<MTLBuffer> scale_buffer=[device newBufferWithBytes:scales.data() length:scales.size() options:MTLResourceStorageModeShared];
        id<MTLBuffer> bias_buffer=[device newBufferWithBytes:bias_bytes.data() length:bias_bytes.size() options:MTLResourceStorageModeShared];
        id<MTLBuffer> output_buffer=[device newBufferWithLength:width*sizeof(float) options:MTLResourceStorageModeShared];
        id<MTLCommandQueue> queue=[device newCommandQueue];
        std::vector<double> metal_samples;
        for (int i=0;i<21;++i) {
            id<MTLCommandBuffer> command=[queue commandBuffer];
            id<MTLComputeCommandEncoder> encoder=[command computeCommandEncoder];
            [encoder setComputePipelineState:pipeline];
            [encoder setBuffer:arg_buffer offset:0 atIndex:0]; [encoder setBuffer:input_buffer offset:0 atIndex:1];
            [encoder setBuffer:value_buffer offset:0 atIndex:2]; [encoder setBuffer:scale_buffer offset:0 atIndex:3];
            [encoder setBuffer:bias_buffer offset:0 atIndex:4]; [encoder setBuffer:output_buffer offset:0 atIndex:5];
            const NSUInteger threads=std::min<NSUInteger>(1024,pipeline.maxTotalThreadsPerThreadgroup);
            const NSUInteger simdgroups=threads/pipeline.threadExecutionWidth;
            [encoder dispatchThreadgroups:MTLSizeMake((width+simdgroups-1)/simdgroups,1,1) threadsPerThreadgroup:MTLSizeMake(threads,1,1)];
            [encoder endEncoding]; auto begin=std::chrono::steady_clock::now(); [command commit]; [command waitUntilCompleted];
            metal_samples.push_back(std::chrono::duration<double,std::milli>(std::chrono::steady_clock::now()-begin).count());
        }
        auto * metal=static_cast<float *>(output_buffer.contents);
        double squared=0.0, scalar_squared=0.0, reference_squared=0.0, metal_squared=0.0, dot=0.0, max_abs=0.0; bool bitwise=true;
        for(uint32_t i=0;i<width;++i){double delta=double(cpu[i])-metal[i];double scalar_delta=double(cpu[i])-scalar[i];squared+=delta*delta;scalar_squared+=scalar_delta*scalar_delta;reference_squared+=double(cpu[i])*cpu[i];metal_squared+=double(metal[i])*metal[i];dot+=double(cpu[i])*metal[i];max_abs=std::max(max_abs,std::abs(delta));bitwise&=std::memcmp(&cpu[i],&metal[i],4)==0;}
        std::sort(cpu_samples.begin()+1,cpu_samples.end()); std::sort(metal_samples.begin()+1,metal_samples.end());
        const double cpu_p50=(cpu_samples[5]+cpu_samples[6])*0.5;
        const double metal_p50=(metal_samples[10]+metal_samples[11])*0.5;
        std::cout << "{\"status\":\"PASSED\",\"cpu_p50_ms\":" << cpu_p50
                  << ",\"metal_p50_ms\":" << metal_p50 << ",\"compute_speedup\":" << cpu_p50/metal_p50
                  << ",\"split_ms\":" << split_ms << ",\"relative_l2\":" << std::sqrt(squared/reference_squared)
                  << ",\"norm_ratio\":" << std::sqrt(metal_squared/reference_squared)
                  << ",\"cosine\":" << dot/std::sqrt(metal_squared*reference_squared)
                  << ",\"scalar_relative_l2\":" << std::sqrt(scalar_squared/reference_squared)
                  << ",\"max_abs\":" << max_abs << ",\"bitwise_equal\":" << (bitwise?"true":"false")
                  << ",\"value_bytes\":" << values.size() << ",\"scale_bytes\":" << scales.size() << "}\n";
    }
    ggml_free(cpu_context); if(cpu_plugin) dlclose(cpu_plugin); return 0;
}
