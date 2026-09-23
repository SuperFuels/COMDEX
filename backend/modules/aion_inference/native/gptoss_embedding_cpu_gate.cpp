#include <cmath>
#include <dlfcn.h>
#include <fstream>
#include <iostream>
#include <string>
#include <vector>
#include "ggml.h"
using compute_function = ggml_status (*)(ggml_context *, ggml_cgraph *, int);
static bool read_exact(const std::string & p, void * d, size_t n){std::ifstream f(p,std::ios::binary|std::ios::ate);if(!f||size_t(f.tellg())!=n)return false;f.seekg(0);f.read((char*)d,n);return f.good();}
int main(int argc,char**argv){
 if(argc!=4){std::cerr<<"usage: embedding ROW OUTPUT THREADS\n";return 2;}
 void*p=dlopen("/opt/homebrew/Cellar/ggml/0.23.0/libexec/libggml-cpu-apple_m2_m3.so",RTLD_NOW|RTLD_LOCAL);if(!p)return 3;
 auto compute=(compute_function)dlsym(p,"ggml_graph_compute_with_ctx");if(!compute)return 4;
 std::vector<char>mem(16*1024*1024);auto*ctx=ggml_init({mem.size(),mem.data(),false});
 auto*w=ggml_new_tensor_2d(ctx,GGML_TYPE_Q5_0,2880,1);if(!read_exact(argv[1],w->data,ggml_nbytes(w)))return 5;
 auto*idx=ggml_new_tensor_1d(ctx,GGML_TYPE_I32,1);*(int32_t*)idx->data=0;
 auto*out=ggml_get_rows(ctx,w,idx);auto*g=ggml_new_graph_custom(ctx,GGML_DEFAULT_GRAPH_SIZE,false);ggml_build_forward_expand(g,out);
 if(compute(ctx,g,std::stoi(argv[3]))!=GGML_STATUS_SUCCESS)return 6;
 std::ofstream f(argv[2],std::ios::binary|std::ios::trunc);f.write((char*)out->data,ggml_nbytes(out));if(!f.good())return 7;
 double sum=0;bool finite=true;for(int i=0;i<2880;++i){float x=((float*)out->data)[i];sum+=x;finite&=std::isfinite(x);}
 std::cout<<"{\"schema\":\"aion.gptoss.embedding-row-cpu.v1\",\"checksum\":"<<sum<<",\"finite\":"<<(finite?"true":"false")<<"}\n";
 ggml_free(ctx);dlclose(p);return finite?0:8;
}
