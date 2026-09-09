#include <algorithm>
#include <array>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <iostream>
#include <string>
#include <vector>

#include "ggml-backend.h"
#include "ggml.h"
#include "llama.h"

struct route_state {
    std::array<std::array<int32_t, 8>, 48> routes{};
    std::array<bool, 48> seen{};
    bool invalid = false;
};

static bool capture_route(ggml_tensor * tensor, bool ask, void * opaque) {
    const char * name = ggml_get_name(tensor);
    constexpr const char * prefix = "ffn_moe_topk-";
    if (std::strncmp(name, prefix, std::strlen(prefix)) != 0) {
        return false;
    }
    if (ask) {
        return true;
    }

    auto * state = static_cast<route_state *>(opaque);
    const int layer = std::atoi(name + std::strlen(prefix));
    if (layer < 0 || layer >= 48 || tensor->type != GGML_TYPE_I32 ||
            ggml_nelements(tensor) != 8) {
        state->invalid = true;
        return true;
    }
    ggml_backend_tensor_get(tensor, state->routes[layer].data(), 0,
                            sizeof(state->routes[layer]));
    auto sorted = state->routes[layer];
    std::sort(sorted.begin(), sorted.end());
    if (sorted.front() < 0 || sorted.back() >= 128 ||
            std::adjacent_find(sorted.begin(), sorted.end()) != sorted.end()) {
        state->invalid = true;
    }
    state->seen[layer] = true;
    return true;
}

int main(int argc, char ** argv) {
    if (argc != 2) {
        std::cerr << "usage: qwen_route_capture MODEL.gguf\n";
        return 2;
    }
    llama_backend_init();
    llama_model_params model_params = llama_model_default_params();
    model_params.n_gpu_layers = 0;
    model_params.load_mode = LLAMA_LOAD_MODE_MMAP;
    model_params.lazy_mode = LLAMA_LAZY_MODE_AUTO;
    model_params.use_extra_bufts = false;

    llama_model * model = llama_model_load_from_file(argv[1], model_params);
    if (model == nullptr) {
        llama_backend_free();
        return 3;
    }

    route_state state;
    llama_context_params context_params = llama_context_default_params();
    context_params.n_ctx = 64;
    context_params.n_batch = 8;
    context_params.n_ubatch = 8;
    context_params.n_threads = 8;
    context_params.n_threads_batch = 8;
    context_params.offload_kqv = false;
    context_params.op_offload = false;
    context_params.cb_eval = capture_route;
    context_params.cb_eval_user_data = &state;
    llama_context * context = llama_init_from_model(model, context_params);
    if (context == nullptr) {
        llama_model_free(model);
        llama_backend_free();
        return 4;
    }

    const std::string prompt = "Hello";
    const llama_vocab * vocab = llama_model_get_vocab(model);
    int32_t count = llama_tokenize(vocab, prompt.c_str(), prompt.size(), nullptr, 0,
                                   true, true);
    if (count >= 0) {
        state.invalid = true;
    } else {
        std::vector<llama_token> tokens(static_cast<size_t>(-count));
        count = llama_tokenize(vocab, prompt.c_str(), prompt.size(), tokens.data(),
                               tokens.size(), true, true);
        if (count <= 0 || llama_decode(context, llama_batch_get_one(tokens.data(), count)) != 0) {
            state.invalid = true;
        }
    }

    const bool complete = std::all_of(state.seen.begin(), state.seen.end(),
                                      [](bool value) { return value; });
    std::cout << "{\"schema\":\"aion.qwen3moe.real-route.v1\","
              << "\"prompt\":\"Hello\",\"complete\":"
              << (complete && !state.invalid ? "true" : "false") << ",\"layers\":[";
    for (int layer = 0; layer < 48; ++layer) {
        if (layer) std::cout << ',';
        std::cout << "{\"layer\":" << layer << ",\"experts\":[";
        for (int expert = 0; expert < 8; ++expert) {
            if (expert) std::cout << ',';
            std::cout << state.routes[layer][expert];
        }
        std::cout << "]}";
    }
    std::cout << "]}\n";

    llama_free(context);
    llama_model_free(model);
    llama_backend_free();
    return complete && !state.invalid ? 0 : 5;
}
