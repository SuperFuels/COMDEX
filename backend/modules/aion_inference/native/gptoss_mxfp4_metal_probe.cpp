#include <algorithm>
#include <chrono>
#include <cmath>
#include <fstream>
#include <iostream>
#include <string>
#include <vector>

#include "ggml.h"
#include "ggml-alloc.h"
#include "ggml-backend.h"

static bool read_exact(const std::string & path, std::vector<char> & value) {
    std::ifstream input(path, std::ios::binary | std::ios::ate);
    if (!input) return false;
    value.resize(static_cast<size_t>(input.tellg()));
    input.seekg(0);
    input.read(value.data(), static_cast<std::streamsize>(value.size()));
    return input.good();
}

int main(int argc, char ** argv) {
    if (argc != 8 && argc != 9) {
        std::cerr << "usage: probe INPUT GATE_W GATE_B UP_W UP_B DOWN_W DOWN_B [OUTPUT]\n";
        return 2;
    }
    ggml_backend_reg_t registration = ggml_backend_load(
        "/opt/homebrew/Cellar/ggml/0.23.0/libexec/libggml-metal.so");
    if (!registration) return 3;
    ggml_backend_dev_t device = ggml_backend_dev_by_type(GGML_BACKEND_DEVICE_TYPE_GPU);
    if (!device) return 4;
    ggml_backend_t backend = ggml_backend_dev_init(device, nullptr);
    if (!backend) return 5;
    constexpr int64_t width=2880;
    std::vector<std::vector<char>> values(7);
    for(int i=0;i<7;++i)if(!read_exact(argv[i+1],values[i]))return 6;
    if(values[0].size()%(width*sizeof(float))!=0)return 11;
    const int64_t batch=values[0].size()/(width*sizeof(float));

    std::vector<char> metadata(16*1024*1024);
    ggml_context * context=ggml_init({metadata.size(),metadata.data(),true});
    auto * input=ggml_new_tensor_2d(context,GGML_TYPE_F32,width,batch);
    auto * gate_w=ggml_new_tensor_2d(context,GGML_TYPE_MXFP4,width,width);
    auto * gate_b=ggml_new_tensor_1d(context,GGML_TYPE_F32,width);
    auto * up_w=ggml_new_tensor_2d(context,GGML_TYPE_MXFP4,width,width);
    auto * up_b=ggml_new_tensor_1d(context,GGML_TYPE_F32,width);
    auto * down_w=ggml_new_tensor_2d(context,GGML_TYPE_MXFP4,width,width);
    auto * down_b=ggml_new_tensor_1d(context,GGML_TYPE_F32,width);
    auto * gate=ggml_add(context,ggml_mul_mat(context,gate_w,input),gate_b);
    auto * up=ggml_add(context,ggml_mul_mat(context,up_w,input),up_b);
    auto * hidden=ggml_swiglu_oai(context,gate,up,1.702f,7.0f);
    auto * output=ggml_add(context,ggml_mul_mat(context,down_w,hidden),down_b);
    auto * graph=ggml_new_graph_custom(context,GGML_DEFAULT_GRAPH_SIZE,false);
    ggml_build_forward_expand(graph,output);
    bool supported=true;
    for(int i=0;i<ggml_graph_n_nodes(graph);++i)
        supported &= ggml_backend_dev_supports_op(device,ggml_graph_node(graph,i));
    if(!supported) {
        std::cout << "{\"status\":\"UNSUPPORTED\",\"device\":\""
                  << ggml_backend_dev_name(device) << "\"}\n";
        return 20;
    }
    auto * buffer=ggml_backend_alloc_ctx_tensors(context,backend);
    if(!buffer)return 7;
    ggml_tensor * leaves[]={input,gate_w,gate_b,up_w,up_b,down_w,down_b};
    const auto upload_begin=std::chrono::steady_clock::now();
    for(int i=0;i<7;++i)ggml_backend_tensor_set(leaves[i],values[i].data(),0,values[i].size());
    const auto upload_end=std::chrono::steady_clock::now();
    std::vector<double> compute_samples;
    for(int repetition=0;repetition<9;++repetition) {
        const auto compute_begin=std::chrono::steady_clock::now();
        if(ggml_backend_graph_compute(backend,graph)!=GGML_STATUS_SUCCESS)return 8;
        ggml_backend_synchronize(backend);
        compute_samples.push_back(std::chrono::duration<double,std::milli>(
            std::chrono::steady_clock::now()-compute_begin).count());
    }
    std::vector<float> result(width*batch);
    ggml_backend_tensor_get(output,result.data(),0,result.size()*sizeof(float));
    if(argc==9) {
        std::ofstream output_file(argv[8],std::ios::binary|std::ios::trunc);
        output_file.write(reinterpret_cast<const char *>(result.data()),result.size()*sizeof(float));
        if(!output_file.good())return 10;
    }
    double checksum=0.0;bool finite=true;
    for(float value:result){checksum+=value;finite&=std::isfinite(value);}
    const double upload_ms=std::chrono::duration<double,std::milli>(upload_end-upload_begin).count();
    std::vector<double> warm(compute_samples.begin()+1,compute_samples.end());
    std::sort(warm.begin(),warm.end());
    const double warm_p50=(warm[3]+warm[4])*0.5;
    std::cout << "{\"status\":\"" << (finite?"PASSED":"FAILED")
              << "\",\"device\":\"" << ggml_backend_dev_name(device)
              << "\",\"all_ops_supported\":" << (supported?"true":"false")
              << ",\"batch\":" << batch
              << ",\"upload_ms\":" << upload_ms << ",\"first_compute_ms\":" << compute_samples[0]
              << ",\"warm_p50_ms\":" << warm_p50 << ",\"compute_samples_ms\":[";
    for(size_t i=0;i<compute_samples.size();++i)std::cout<<(i?",":"")<<compute_samples[i];
    std::cout << "],\"checksum\":" << checksum << "}\n";
    ggml_backend_buffer_free(buffer);
    ggml_backend_free(backend);
    ggml_free(context);
    ggml_backend_unload(registration);
    return finite?0:9;
}
