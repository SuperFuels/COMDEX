#include <algorithm>
#include <cmath>
#include <dlfcn.h>
#include <fstream>
#include <iostream>
#include <vector>
#include "ggml.h"
using compute_function = ggml_status (*)(ggml_context *, ggml_cgraph *, int);
static bool read_exact(const char*p,void*d,size_t n){std::ifstream f(p,std::ios::binary|std::ios::ate);if(!f||size_t(f.tellg())!=n)return false;f.seekg(0);f.read((char*)d,n);return f.good();}
int main(int argc,char**argv){
 if(argc!=6){std::cerr<<"usage: output WEIGHT NORM HIDDEN LOGITS THREADS\n";return 2;}
 void*p=dlopen("/opt/homebrew/Cellar/ggml/0.23.0/libexec/libggml-cpu-apple_m2_m3.so",RTLD_NOW|RTLD_LOCAL);if(!p)return 3;
 auto compute=(compute_function)dlsym(p,"ggml_graph_compute_with_ctx");if(!compute)return 4;
 std::vector<char>mem(768ULL*1024*1024);auto*ctx=ggml_init({mem.size(),mem.data(),false});if(!ctx)return 5;
 auto*w=ggml_new_tensor_2d(ctx,GGML_TYPE_Q8_0,2880,201088);auto*n=ggml_new_tensor_1d(ctx,GGML_TYPE_F32,2880);auto*h=ggml_new_tensor_1d(ctx,GGML_TYPE_F32,2880);
 if(!read_exact(argv[1],w->data,ggml_nbytes(w))||!read_exact(argv[2],n->data,ggml_nbytes(n))||!read_exact(argv[3],h->data,ggml_nbytes(h)))return 6;
 auto*normalized=ggml_mul(ctx,ggml_rms_norm(ctx,h,1.0e-5f),n);auto*logits=ggml_mul_mat(ctx,w,normalized);
 auto*g=ggml_new_graph_custom(ctx,GGML_DEFAULT_GRAPH_SIZE,false);ggml_build_forward_expand(g,logits);if(compute(ctx,g,std::stoi(argv[5]))!=GGML_STATUS_SUCCESS)return 7;
 std::ofstream f(argv[4],std::ios::binary|std::ios::trunc);f.write((char*)logits->data,ggml_nbytes(logits));if(!f.good())return 8;
 auto*v=(float*)logits->data;int best=0;double sum=0;bool finite=true;for(int i=0;i<201088;++i){if(v[i]>v[best])best=i;sum+=v[i];finite&=std::isfinite(v[i]);}
 int second=best==0?1:0;for(int i=0;i<201088;i++)if(i!=best&&v[i]>v[second])second=i;
 std::cout<<"{\"schema\":\"aion.gptoss.output-cpu.v1\",\"argmax_token_id\":"<<best<<",\"max_logit\":"<<v[best]<<",\"second_token_id\":"<<second<<",\"second_logit\":"<<v[second]<<",\"margin\":"<<(v[best]-v[second])<<",\"logit_checksum\":"<<sum<<",\"finite\":"<<(finite?"true":"false")<<"}\n";
 ggml_free(ctx);dlclose(p);return finite?0:9;
}
