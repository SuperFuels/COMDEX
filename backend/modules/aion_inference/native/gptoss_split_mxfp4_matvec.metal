// SPDX-License-Identifier: Apache-2.0
// MXFP4 unpacking follows the public OpenAI gpt-oss Metal implementation,
// adapted here for one GGUF-derived matrix, split scale/value streams, and F32 bias.
#include <metal_stdlib>
#include <metal_simdgroup>
using namespace metal;

struct MatvecArgs {
    uint blocks_per_row;
    uint rows;
};

constant float aion_mxfp4_grid[16] = {
    0.0f,0.5f,1.0f,1.5f,2.0f,3.0f,4.0f,6.0f,
    -0.0f,-0.5f,-1.0f,-1.5f,-2.0f,-3.0f,-4.0f,-6.0f
};

kernel void aion_split_mxfp4_matvec(
    constant MatvecArgs & args [[buffer(0)]],
    device const float * input [[buffer(1)]],
    device const uchar * weight_blocks [[buffer(2)]],
    device const uchar * weight_scales [[buffer(3)]],
    device const float * bias [[buffer(4)]],
    device float * output [[buffer(5)]],
    uint group [[threadgroup_position_in_grid]],
    uint simd_lane [[thread_index_in_simdgroup]],
    uint simd_index [[simdgroup_index_in_threadgroup]],
    uint simdgroups [[simdgroups_per_threadgroup]]) {
    const uint row = group * simdgroups + simd_index;
    if (row >= args.rows) return;
    const uint blocks = args.blocks_per_row;
    float partial = 0.0f;
    for (uint block = simd_lane; block < blocks; block += 32) {
        const uint offset = row * blocks + block;
        const device uchar * codes = weight_blocks + offset * 16;
        const float scale = as_type<float>(static_cast<uint>(weight_scales[offset]) << 23);
        // Decode four values per iteration.  This deliberately keeps the
        // transparent lookup-table arithmetic of the scalar correctness
        // baseline while cutting loop/index work by four.
        for (uint element=0; element<32; element += 4) {
            const uchar first = codes[element >> 1];
            const uchar second = codes[(element >> 1) + 1];
            const float4 decoded = float4(
                aion_mxfp4_grid[first & 15],
                aion_mxfp4_grid[first >> 4],
                aion_mxfp4_grid[second & 15],
                aion_mxfp4_grid[second >> 4]) * scale;
            const float4 activation = *reinterpret_cast<device const float4 *>(
                input + block * 32 + element);
            partial += dot(activation, decoded);
        }
    }
    float sum = simd_sum(partial);
    if (simd_is_first()) output[row] = sum + bias[row];
}
