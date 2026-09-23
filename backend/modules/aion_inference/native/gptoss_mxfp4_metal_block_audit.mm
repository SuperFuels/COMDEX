#import <Foundation/Foundation.h>
#import <Metal/Metal.h>
#include <cmath>
#include <cstdio>
#include <cstring>
#include <ggml.h>

// Compatibility microgate only: no expert arithmetic or timing claim.
int main(int argc,char ** argv) { @autoreleasepool {
    bool bit_decode=argc==2 && std::strcmp(argv[1],"--bit-decode")==0;
    id<MTLDevice> device=MTLCreateSystemDefaultDevice();
    if(!device){fprintf(stderr,"Metal unavailable\n");return 2;}
    NSString * source=@R"METAL(
#include <metal_stdlib>
using namespace metal;
kernel void unpack(device const uchar * packed [[buffer(0)]],
                   device float * output [[buffer(1)]], uint index [[thread_position_in_grid]]) {
    if(index>=160)return;
    uint block=index/32, local=index%32;
    uchar byte=packed[block*17+1+local%16];
    uint code=local<16 ? byte&15 : byte>>4;
    const float grid[16]={0.f,.5f,1.f,1.5f,2.f,3.f,4.f,6.f,0.f,-.5f,-1.f,-1.5f,-2.f,-3.f,-4.f,-6.f};
    output[index]=grid[code]*ldexp(1.f,int(packed[block*17])-127);
}
kernel void unpack_bits(device const uchar * packed [[buffer(0)]],
                        device uint * output [[buffer(1)]], uint index [[thread_position_in_grid]]) {
    if(index>=160)return;
    uint block=index/32, local=index%32;
    uchar byte=packed[block*17+1+local%16];
    uint code=local<16 ? byte&15 : byte>>4, magnitude=code&7, exponent=packed[block*17];
    const uint zero[8]={0,0x00200000,0x00400000,0x00600000,0x00800000,0x00c00000,0x01000000,0x01400000};
    const uint one[8]={0,0x00400000,0x00800000,0x00c00000,0x01000000,0x01400000,0x01800000,0x01c00000};
    const int shift[8]={0,-1,0,0,1,1,2,2};
    const uint fraction[8]={0,0,0,0x00400000,0,0x00400000,0,0x00400000};
    uint bits=magnitude==0 ? 0 : exponent==0 ? zero[magnitude] : exponent==1 ? one[magnitude] : ((exponent+shift[magnitude])<<23)|fraction[magnitude];
    if(magnitude && (code&8))bits|=0x80000000;
    output[index]=bits;
}
)METAL";
    NSError * error=nil;
    MTLCompileOptions * options=[MTLCompileOptions new];
    options.fastMathEnabled=NO;
    id<MTLLibrary> library=[device newLibraryWithSource:source options:options error:&error];
    if(!library){fprintf(stderr,"%s\n",error.description.UTF8String);return 3;}
    id<MTLComputePipelineState> pipeline=[device newComputePipelineStateWithFunction:[library newFunctionWithName:bit_decode?@"unpack_bits":@"unpack"] error:&error];
    if(!pipeline){fprintf(stderr,"%s\n",error.description.UTF8String);return 4;}
    const unsigned char exponents[5]={0,1,100,127,200};
    unsigned char packed[85];float expected[160];
    for(int b=0;b<5;b++) {
        packed[b*17]=exponents[b];
        for(int i=0;i<16;i++)packed[b*17+1+i]=i|((15-i)<<4);
        ggml_get_type_traits(GGML_TYPE_MXFP4)->to_float(packed+b*17,expected+b*32,32);
    }
    id<MTLBuffer> input=[device newBufferWithBytes:packed length:sizeof(packed) options:MTLResourceStorageModeShared];
    id<MTLBuffer> output=[device newBufferWithLength:sizeof(expected) options:MTLResourceStorageModeShared];
    id<MTLCommandQueue> queue=[device newCommandQueue];
    id<MTLCommandBuffer> command=[queue commandBuffer];
    id<MTLComputeCommandEncoder> encoder=[command computeCommandEncoder];
    [encoder setComputePipelineState:pipeline];[encoder setBuffer:input offset:0 atIndex:0];[encoder setBuffer:output offset:0 atIndex:1];
    [encoder dispatchThreads:MTLSizeMake(160,1,1) threadsPerThreadgroup:MTLSizeMake(32,1,1)];
    [encoder endEncoding];[command commit];[command waitUntilCompleted];
    if(command.status!=MTLCommandBufferStatusCompleted){fprintf(stderr,"Metal command failed\n");return 5;}
    int mismatch=0,by_exponent[5]={};auto * actual=static_cast<const float *>(output.contents);
    for(int i=0;i<160;i++)if(memcmp(actual+i,expected+i,sizeof(float))){mismatch++;by_exponent[i/32]++;}
    printf("{\"status\":\"%s\",\"values\":160,\"bitwise_mismatches\":%d,\"mismatches_at_exponents_0_1_100_127_200\":[%d,%d,%d,%d,%d],\"device\":\"%s\",\"claim_boundary\":\"Synthetic block decode only; no neural arithmetic, speed or quality claim\"}\n",mismatch?"FAILED":"PASSED",mismatch,by_exponent[0],by_exponent[1],by_exponent[2],by_exponent[3],by_exponent[4],device.name.UTF8String);
    return mismatch?1:0;
}}
