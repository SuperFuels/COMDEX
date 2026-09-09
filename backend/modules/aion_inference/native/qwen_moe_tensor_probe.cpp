#include <cstdint>
#include <cstring>
#include <iostream>
#include <set>
#include <string>
#include <vector>

#include "ggml.h"
#include "llama.h"

struct probe_state {
    std::set<std::string> emitted;
};

static bool probe_tensor(ggml_tensor * tensor, bool ask, void * opaque) {
    const char * name = ggml_get_name(tensor);
    if (std::strstr(name, "ffn_moe") == nullptr &&
        std::strstr(name, "ffn_final_moe") == nullptr) {
        return false;
    }
    if (ask) return true;
    auto * state = static_cast<probe_state *>(opaque);
    if (!state->emitted.insert(name).second) return true;
    std::cout << "{\"name\":\"" << name << "\",\"type\":" << tensor->type
              << ",\"ne\":[" << tensor->ne[0] << ',' << tensor->ne[1] << ','
              << tensor->ne[2] << ',' << tensor->ne[3] << "],\"nb\":["
              << tensor->nb[0] << ',' << tensor->nb[1] << ',' << tensor->nb[2]
              << ',' << tensor->nb[3] << "]}\n";
    return true;
}

int main(int argc, char ** argv) {
    if (argc != 2) {
        std::cerr << "usage: qwen_moe_tensor_probe MODEL.gguf\n";
        return 2;
    }
    llama_backend_init();
    llama_model_params mp = llama_model_default_params();
    mp.n_gpu_layers = 0;
    mp.load_mode = LLAMA_LOAD_MODE_MMAP;
    mp.lazy_mode = LLAMA_LAZY_MODE_AUTO;
    mp.use_extra_bufts = false;
    llama_model * model = llama_model_load_from_file(argv[1], mp);
    if (model == nullptr) return 3;
    probe_state state;
    llama_context_params cp = llama_context_default_params();
    cp.n_ctx = 16;
    cp.n_batch = 16;
    cp.n_ubatch = 16;
    cp.n_threads = 8;
    cp.n_threads_batch = 8;
    cp.offload_kqv = false;
    cp.op_offload = false;
    cp.cb_eval = probe_tensor;
    cp.cb_eval_user_data = &state;
    llama_context * context = llama_init_from_model(model, cp);
    if (context == nullptr) return 4;
    const llama_vocab * vocab = llama_model_get_vocab(model);
    const std::string prompt = "Hello";
    int32_t count = llama_tokenize(vocab, prompt.c_str(), prompt.size(), nullptr, 0, true, true);
    if (count >= 0) return 5;
    std::vector<llama_token> tokens(static_cast<size_t>(-count));
    count = llama_tokenize(vocab, prompt.c_str(), prompt.size(), tokens.data(), tokens.size(), true, true);
    const int result = llama_decode(context, llama_batch_get_one(tokens.data(), count));
    llama_free(context);
    llama_model_free(model);
    llama_backend_free();
    return result == 0 ? 0 : 6;
}
