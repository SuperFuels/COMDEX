#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <sstream>
#include <string>
#include <vector>

#include "ggml.h"
#include "ggml-backend.h"

static bool read_exact(const std::string & path, std::vector<char> & value) {
    std::ifstream input(path, std::ios::binary | std::ios::ate);
    if (!input) return false;
    value.resize(static_cast<size_t>(input.tellg()));
    input.seekg(0);
    input.read(value.data(), static_cast<std::streamsize>(value.size()));
    return input.good();
}

static std::vector<float> split_floats(const std::string & text) {
    std::vector<float> result;
    std::stringstream stream(text);
    std::string item;
    while (std::getline(stream, item, ',')) result.push_back(std::stof(item));
    return result;
}

int main(int argc, char ** argv) {
    if (argc != 4) {
        std::cerr << "usage: metal-route COMPONENT_DIR GATES_CSV OUTPUT\n";
        return 2;
    }
    const auto gates = split_floats(argv[2]);
    if (gates.size() != 4) return 3;
    auto registration = ggml_backend_load(
        "/opt/homebrew/Cellar/ggml/0.23.0/libexec/libggml-metal.so");
    if (!registration) return 4;
    auto device = ggml_backend_dev_by_type(GGML_BACKEND_DEVICE_TYPE_GPU);
    if (!device) return 5;
    auto backend = ggml_backend_dev_init(device, nullptr);
    if (!backend) return 6;

    constexpr int64_t width = 2880;
    std::vector<char> metadata(32 * 1024 * 1024);
    auto context = ggml_init({metadata.size(), metadata.data(), true});
    if (!context) return 7;
    auto input = ggml_new_tensor_1d(context, GGML_TYPE_F32, width);
    std::vector<float> input_values(width);
    for (int64_t i = 0; i < width; ++i)
        input_values[i] = std::sin(static_cast<float>(i) * 0.00390625f);
    if (const char * input_path = std::getenv("AION_INPUT_PATH")) {
        std::ifstream input_file(input_path, std::ios::binary | std::ios::ate);
        if (!input_file || static_cast<size_t>(input_file.tellg()) != input_values.size() * sizeof(float)) return 21;
        input_file.seekg(0);
        input_file.read(reinterpret_cast<char *>(input_values.data()),
                        static_cast<std::streamsize>(input_values.size() * sizeof(float)));
        if (!input_file.good()) return 22;
    }

    const char * names[] = {"gate-weight", "gate-bias", "up-weight", "up-bias",
                            "down-weight", "down-bias"};
    std::vector<ggml_tensor *> leaves{input};
    std::vector<std::vector<char>> values(24);
    ggml_tensor * combined = nullptr;
    for (int position = 0; position < 4; ++position) {
        auto gate_w = ggml_new_tensor_2d(context, GGML_TYPE_MXFP4, width, width);
        auto gate_b = ggml_new_tensor_1d(context, GGML_TYPE_F32, width);
        auto up_w = ggml_new_tensor_2d(context, GGML_TYPE_MXFP4, width, width);
        auto up_b = ggml_new_tensor_1d(context, GGML_TYPE_F32, width);
        auto down_w = ggml_new_tensor_2d(context, GGML_TYPE_MXFP4, width, width);
        auto down_b = ggml_new_tensor_1d(context, GGML_TYPE_F32, width);
        ggml_tensor * tensors[] = {gate_w, gate_b, up_w, up_b, down_w, down_b};
        for (int component = 0; component < 6; ++component) {
            const auto path = std::string(argv[1]) + "/" + std::to_string(position)
                            + "-" + names[component] + ".bin";
            if (!read_exact(path, values[position * 6 + component])) return 8;
            if (values[position * 6 + component].size() != ggml_nbytes(tensors[component]))
                return 9;
            leaves.push_back(tensors[component]);
        }
        auto gate = ggml_add(context, ggml_mul_mat(context, gate_w, input), gate_b);
        auto up = ggml_add(context, ggml_mul_mat(context, up_w, input), up_b);
        auto hidden = ggml_swiglu_oai(context, gate, up, 1.702f, 7.0f);
        auto expert = ggml_add(context, ggml_mul_mat(context, down_w, hidden), down_b);
        expert = ggml_scale(context, expert, gates[position]);
        combined = combined ? ggml_add(context, combined, expert) : expert;
    }
    auto graph = ggml_new_graph_custom(context, GGML_DEFAULT_GRAPH_SIZE, false);
    ggml_build_forward_expand(graph, combined);
    for (int node = 0; node < ggml_graph_n_nodes(graph); ++node) {
        if (!ggml_backend_dev_supports_op(device, ggml_graph_node(graph, node))) {
            std::cout << "{\"status\":\"UNSUPPORTED\"}\n";
            return 20;
        }
    }
    auto buffer = ggml_backend_alloc_ctx_tensors(context, backend);
    if (!buffer) return 10;
    const auto upload_begin = std::chrono::steady_clock::now();
    ggml_backend_tensor_set(input, input_values.data(), 0, input_values.size() * sizeof(float));
    for (size_t index = 1; index < leaves.size(); ++index)
        ggml_backend_tensor_set(leaves[index], values[index - 1].data(), 0,
                                values[index - 1].size());
    const auto upload_end = std::chrono::steady_clock::now();
    std::vector<double> samples;
    for (int repetition = 0; repetition < 11; ++repetition) {
        const auto begin = std::chrono::steady_clock::now();
        if (ggml_backend_graph_compute(backend, graph) != GGML_STATUS_SUCCESS) return 11;
        ggml_backend_synchronize(backend);
        samples.push_back(std::chrono::duration<double, std::milli>(
            std::chrono::steady_clock::now() - begin).count());
    }
    std::vector<float> output(width);
    ggml_backend_tensor_get(combined, output.data(), 0, output.size() * sizeof(float));
    std::ofstream output_file(argv[3], std::ios::binary | std::ios::trunc);
    output_file.write(reinterpret_cast<const char *>(output.data()),
                      output.size() * sizeof(float));
    if (!output_file.good()) return 12;
    std::vector<double> warm(samples.begin() + 1, samples.end());
    std::sort(warm.begin(), warm.end());
    double checksum = 0.0;
    bool finite = true;
    for (float value : output) { checksum += value; finite &= std::isfinite(value); }
    const double upload_ms = std::chrono::duration<double, std::milli>(
        upload_end - upload_begin).count();
    std::cout << "{\"status\":\"" << (finite ? "PASSED" : "FAILED")
              << "\",\"device\":\"" << ggml_backend_dev_name(device)
              << "\",\"upload_ms\":" << upload_ms
              << ",\"first_compute_ms\":" << samples.front()
              << ",\"warm_p50_ms\":" << (warm[4] + warm[5]) * 0.5
              << ",\"warm_p95_ms\":" << warm[9]
              << ",\"checksum\":" << checksum << "}\n";
    ggml_backend_buffer_free(buffer);
    ggml_backend_free(backend);
    ggml_free(context);
    ggml_backend_unload(registration);
    return finite ? 0 : 13;
}
