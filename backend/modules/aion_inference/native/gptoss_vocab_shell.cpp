#include <charconv>
#include <cstdint>
#include <iostream>
#include <string>
#include <vector>

#include "llama.h"

int main(int argc, char ** argv) {
    if (argc < 4) {
        std::cerr << "usage: gptoss_vocab_shell MODEL.gguf tokenize TEXT | chat-tokenize TEXT | detokenize ID...\n";
        return 2;
    }
    llama_backend_init();
    llama_model_params params = llama_model_default_params();
    params.vocab_only = true;
    params.n_gpu_layers = 0;
    params.use_extra_bufts = false;
    llama_model * model = llama_model_load_from_file(argv[1], params);
    if (model == nullptr) return 3;
    const llama_vocab * vocab = llama_model_get_vocab(model);
    int result = 0;
    const std::string mode = argv[2];
    if (mode == "tokenize" || mode == "chat-tokenize") {
        std::string text = argv[3];
        if (mode == "chat-tokenize") {
            const char * chat_template = llama_model_chat_template(model, nullptr);
            const llama_chat_message message = {"user", argv[3]};
            std::vector<char> rendered(16 * 1024);
            int32_t rendered_count = llama_chat_apply_template(
                chat_template, &message, 1, true, rendered.data(), rendered.size());
            if (rendered_count < 0) {
                result = 9;
            } else {
                if (rendered_count > static_cast<int32_t>(rendered.size())) {
                    rendered.resize(static_cast<size_t>(rendered_count));
                    rendered_count = llama_chat_apply_template(
                        chat_template, &message, 1, true, rendered.data(), rendered.size());
                }
                if (rendered_count < 0) result = 10;
                else text.assign(rendered.data(), static_cast<size_t>(rendered_count));
            }
        }
        if (result != 0) {
            llama_model_free(model);
            llama_backend_free();
            return result;
        }
        int32_t count = llama_tokenize(vocab, text.data(), text.size(), nullptr, 0, false, true);
        if (count >= 0) {
            result = 4;
        } else {
            std::vector<llama_token> tokens(static_cast<size_t>(-count));
            count = llama_tokenize(vocab, text.data(), text.size(), tokens.data(), tokens.size(), false, true);
            if (count < 0) {
                result = 5;
            } else {
                for (int32_t index = 0; index < count; ++index) {
                    if (index) std::cout << ',';
                    std::cout << tokens[static_cast<size_t>(index)];
                }
                std::cout << '\n';
            }
        }
    } else if (mode == "detokenize") {
        std::vector<llama_token> tokens;
        for (int index = 3; index < argc; ++index) {
            int32_t value = 0;
            const char * begin = argv[index];
            const char * end = begin + std::char_traits<char>::length(begin);
            if (std::from_chars(begin, end, value).ec != std::errc()) {
                result = 6;
                break;
            }
            tokens.push_back(value);
        }
        if (result == 0) {
            std::vector<char> text(4096);
            int32_t count = llama_detokenize(vocab, tokens.data(), tokens.size(), text.data(), text.size(), false, true);
            if (count < 0) {
                text.resize(static_cast<size_t>(-count));
                count = llama_detokenize(vocab, tokens.data(), tokens.size(), text.data(), text.size(), false, true);
            }
            if (count < 0) {
                result = 7;
            } else {
                std::cout.write(text.data(), count);
                std::cout << '\n';
            }
        }
    } else {
        result = 8;
    }
    llama_model_free(model);
    llama_backend_free();
    return result;
}
