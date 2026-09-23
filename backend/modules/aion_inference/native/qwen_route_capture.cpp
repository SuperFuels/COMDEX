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
    std::array<std::vector<std::array<int32_t, 8>>, 48> routes{};
    int32_t expected_tokens = 0;
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
    const int64_t elements = ggml_nelements(tensor);
    if (layer < 0 || layer >= 48 || tensor->type != GGML_TYPE_I32 ||
            elements <= 0 || elements % 8 != 0) {
        state->invalid = true;
        return true;
    }
    std::vector<int32_t> values(static_cast<size_t>(elements));
    const size_t token_count = static_cast<size_t>(elements / 8);
    ggml_backend_tensor_get_2d(tensor, values.data(), 0, 8 * sizeof(int32_t),
                               token_count, tensor->nb[1], 8 * sizeof(int32_t));
    for (size_t offset = 0; offset < values.size(); offset += 8) {
        std::array<int32_t, 8> route{};
        std::copy_n(values.begin() + offset, 8, route.begin());
        auto sorted = route;
        std::sort(sorted.begin(), sorted.end());
        if (sorted.front() < 0 || sorted.back() >= 128 ||
                std::adjacent_find(sorted.begin(), sorted.end()) != sorted.end()) {
            state->invalid = true;
        }
        state->routes[layer].push_back(route);
    }
    return true;
}

static std::string json_escape(const std::string & value) {
    std::string result;
    for (const char character : value) {
        if (character == '\\' || character == '"') result.push_back('\\');
        result.push_back(character);
    }
    return result;
}

int main(int argc, char ** argv) {
    if (argc < 2 || argc > 3) {
        std::cerr << "usage: qwen_route_capture MODEL.gguf [PROMPT]\n";
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
    context_params.n_batch = 64;
    context_params.n_ubatch = 64;
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

    const std::string prompt = argc == 3 ? argv[2] : "Hello";
    const llama_vocab * vocab = llama_model_get_vocab(model);
    int32_t count = llama_tokenize(vocab, prompt.c_str(), prompt.size(), nullptr, 0,
                                   true, true);
    if (count >= 0) {
        state.invalid = true;
    } else {
        std::vector<llama_token> tokens(static_cast<size_t>(-count));
        count = llama_tokenize(vocab, prompt.c_str(), prompt.size(), tokens.data(),
                               tokens.size(), true, true);
        state.expected_tokens = count;
        if (count <= 0 || llama_decode(context, llama_batch_get_one(tokens.data(), count)) != 0) {
            state.invalid = true;
        }
    }

    bool complete = state.expected_tokens > 0;
    for (size_t layer = 0; layer < state.routes.size(); ++layer) {
        // llama.cpp prunes non-output positions from the final layer because
        // llama_batch_get_one requests logits only for the last prompt token.
        const size_t expected = layer == 47 ? 1 : static_cast<size_t>(state.expected_tokens);
        complete = complete && state.routes[layer].size() == expected;
    }
    std::cout << "{\"schema\":\"aion.qwen3moe.real-route.v1\","
              << "\"prompt\":\"" << json_escape(prompt) << "\",\"token_count\":"
              << state.expected_tokens << ",\"complete\":"
              << (complete && !state.invalid ? "true" : "false") << ",\"layers\":[";
    for (int layer = 0; layer < 48; ++layer) {
        if (layer) std::cout << ',';
        std::cout << "{\"layer\":" << layer << ",\"routes\":[";
        for (size_t token = 0; token < state.routes[layer].size(); ++token) {
            if (token) std::cout << ',';
            std::cout << '[';
            for (int expert = 0; expert < 8; ++expert) {
                if (expert) std::cout << ',';
                std::cout << state.routes[layer][token][expert];
            }
            std::cout << ']';
        }
        std::cout << "]}";
    }
    std::cout << "]}\n";

    llama_free(context);
    llama_model_free(model);
    llama_backend_free();
    return complete && !state.invalid ? 0 : 5;
}
