// SPDX-License-Identifier: Apache-2.0
// Direct split-stream MXFP4 four-expert GPT-OSS route for Apple Metal.
#include <metal_stdlib>
#include <metal_simdgroup>
using namespace metal;

#pragma METAL fp math_mode(safe)
#pragma METAL fp contract(off)

struct RouteArgs { uint blocks_per_row; uint rows; };

constant float mxfp4_grid[16] = {
    0.0f,0.5f,1.0f,1.5f,2.0f,3.0f,4.0f,6.0f,
    -0.0f,-0.5f,-1.0f,-1.5f,-2.0f,-3.0f,-4.0f,-6.0f
};

inline float packed_dot(device const float * input, device const uchar * codes,
                        device const uchar * scales, uint blocks, uint lane) {
    device const float4 * input4 = reinterpret_cast<device const float4 *>(input) + lane * 8;
    device const uint4 * weight4 = reinterpret_cast<device const uint4 *>(codes) + lane;
    device const uchar * scale = scales + lane;
    uint iterations = (blocks - lane + 31) / 32;
    float4 sum4 = 0.0f;
    do {
        const uint4 wblock = *weight4;
        // The half-bit unpack encodes the E2M1 grid at 2^-14.  Re-bias the
        // GGUF E8M0 exponent exactly as the official gpt-oss Metal loader.
        const float wscale = as_type<float>((uint(*scale) + 14u) << 23);
        uint4 even = (wblock + wblock) & 0x1E1E1E1Eu;
        uint4 odd = (wblock >> 3) & 0x1E1E1E1Eu;
        even = (even + 0x70707070u) & 0x8E8E8E8Eu;
        odd = (odd + 0x70707070u) & 0x8E8E8E8Eu;
        const uint4 e26 = even & 0xFF00FF00u;
        const uint4 e04 = (even << 8) & 0xFF00FF00u;
        const uint4 o37 = odd & 0xFF00FF00u;
        const uint4 o15 = (odd << 8) & 0xFF00FF00u;
        const float4 w048C = float4(as_type<half4>(e04.xy));
        const float4 wGKOS = float4(as_type<half4>(e04.zw));
        const float4 w26AE = float4(as_type<half4>(e26.xy));
        const float4 wIMQU = float4(as_type<half4>(e26.zw));
        const float4 w159D = float4(as_type<half4>(o15.xy));
        const float4 wHLPT = float4(as_type<half4>(o15.zw));
        const float4 w37BF = float4(as_type<half4>(o37.xy));
        const float4 wJNRV = float4(as_type<half4>(o37.zw));
        const float4 w0 = {w048C.x,w159D.x,w26AE.x,w37BF.x};
        const float4 w1 = {w048C.y,w159D.y,w26AE.y,w37BF.y};
        const float4 w2 = {w048C.z,w159D.z,w26AE.z,w37BF.z};
        const float4 w3 = {w048C.w,w159D.w,w26AE.w,w37BF.w};
        const float4 w4 = {wGKOS.x,wHLPT.x,wIMQU.x,wJNRV.x};
        const float4 w5 = {wGKOS.y,wHLPT.y,wIMQU.y,wJNRV.y};
        const float4 w6 = {wGKOS.z,wHLPT.z,wIMQU.z,wJNRV.z};
        const float4 w7 = {wGKOS.w,wHLPT.w,wIMQU.w,wJNRV.w};
        float4 p0=input4[0]*w0, p1=input4[1]*w1;
        p0=fma(input4[2],w2,p0); p1=fma(input4[3],w3,p1);
        p0=fma(input4[4],w4,p0); p1=fma(input4[5],w5,p1);
        p0=fma(input4[6],w6,p0); p1=fma(input4[7],w7,p1);
        sum4=fma(p0,wscale,sum4); sum4=fma(p1,wscale,sum4);
        weight4 += 32; scale += 32; input4 += 8 * 32;
    } while (--iterations != 0);
    const float2 sum2 = sum4.xy + sum4.zw;
    return simd_sum(sum2.x + sum2.y);
}

// Matrices 0,2,4,6 are gate; 1,3,5,7 are up.
kernel void route_gate_up(
    constant RouteArgs & args [[buffer(0)]], device const float * input [[buffer(1)]],
    device const uchar * values [[buffer(2)]], device const uchar * scales [[buffer(3)]],
    device const float * biases [[buffer(4)]], device float * projected [[buffer(5)]],
    uint2 group [[threadgroup_position_in_grid]], uint lane [[thread_index_in_simdgroup]],
    uint simd_index [[simdgroup_index_in_threadgroup]],
    uint simdgroups [[simdgroups_per_threadgroup]]) {
    const uint matrix = group.y;
    const uint row = group.x * simdgroups + simd_index;
    if (matrix >= 8 || row >= args.rows) return;
    const size_t matrix_blocks = size_t(args.rows) * args.blocks_per_row;
    const size_t offset = size_t(matrix) * matrix_blocks + size_t(row) * args.blocks_per_row;
    const float sum = packed_dot(input, values + offset * 16, scales + offset,
                                 args.blocks_per_row, lane);
    if (simd_is_first()) projected[matrix * args.rows + row] = sum + biases[matrix * args.rows + row];
}

kernel void route_swiglu(
    device const float * projected [[buffer(0)]], device float * hidden [[buffer(1)]],
    uint index [[thread_position_in_grid]]) {
    if (index >= 4 * 2880) return;
    const uint expert = index / 2880;
    const uint element = index % 2880;
    const float gate = clamp(projected[(expert * 2) * 2880 + element], -7.0f, 7.0f);
    const float up = projected[(expert * 2 + 1) * 2880 + element];
    hidden[index] = gate / (1.0f + exp(-1.702f * gate)) * (up + 1.0f);
}

kernel void route_down(
    constant RouteArgs & args [[buffer(0)]], device const float * hidden [[buffer(1)]],
    device const uchar * values [[buffer(2)]], device const uchar * scales [[buffer(3)]],
    device const float * biases [[buffer(4)]], device float * expert_output [[buffer(5)]],
    uint2 group [[threadgroup_position_in_grid]], uint lane [[thread_index_in_simdgroup]],
    uint simd_index [[simdgroup_index_in_threadgroup]],
    uint simdgroups [[simdgroups_per_threadgroup]]) {
    const uint expert = group.y;
    const uint row = group.x * simdgroups + simd_index;
    if (expert >= 4 || row >= args.rows) return;
    const size_t matrix_blocks = size_t(args.rows) * args.blocks_per_row;
    const size_t offset = size_t(expert) * matrix_blocks + size_t(row) * args.blocks_per_row;
    const float sum = packed_dot(hidden + expert * args.rows, values + offset * 16,
                                 scales + offset, args.blocks_per_row, lane);
    if (simd_is_first()) expert_output[expert * args.rows + row] = sum + biases[expert * args.rows + row];
}

kernel void route_combine(device const float * expert_output [[buffer(0)]],
                          constant float * gates [[buffer(1)]], device float * output [[buffer(2)]],
                          uint index [[thread_position_in_grid]]) {
    if (index >= 2880) return;
    float sum = 0.0f;
    for (uint expert = 0; expert < 4; ++expert)
        sum = fma(gates[expert], expert_output[expert * 2880 + index], sum);
    output[index] = sum;
}
