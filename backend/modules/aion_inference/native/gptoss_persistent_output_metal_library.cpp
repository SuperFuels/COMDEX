#include <chrono>
#include <cmath>
#include <cstring>
#include <vector>

#include "ggml.h"
#include "ggml-backend.h"

namespace {

struct PersistentOutputMetal {
    static constexpr int64_t width = 2880;
    static constexpr int64_t vocabulary = 201088;

    ggml_backend_reg_t registration = nullptr;
    ggml_backend_dev_t device = nullptr;
    ggml_backend_t backend = nullptr;
    std::vector<char> metadata;
    ggml_context * context = nullptr;
    ggml_tensor * weight = nullptr;
    ggml_tensor * norm = nullptr;
    ggml_tensor * hidden = nullptr;
    ggml_tensor * logits = nullptr;
    ggml_cgraph * graph = nullptr;
    ggml_backend_buffer_t buffer = nullptr;
    const void * source_weight = nullptr;
    bool ready = false;

    void release() {
        // Release the buffer before the backend device.  Metal residency sets
        // assert at process shutdown if live allocations remain registered.
        if (buffer) { ggml_backend_buffer_free(buffer); buffer = nullptr; }
        if (context) { ggml_free(context); context = nullptr; }
        if (backend) { ggml_backend_free(backend); backend = nullptr; }
        if (registration) { ggml_backend_unload(registration); registration = nullptr; }
        ready = false;
    }

    ~PersistentOutputMetal() { release(); }

    int initialise(const void * weight_values, const float * norm_values) {
        registration = ggml_backend_load(
            "/opt/homebrew/Cellar/ggml/0.23.0/libexec/libggml-metal.so");
        if (!registration) return 10;
        device = ggml_backend_dev_by_type(GGML_BACKEND_DEVICE_TYPE_GPU);
        if (!device) return 11;
        backend = ggml_backend_dev_init(device, nullptr);
        if (!backend) return 12;
        metadata.resize(16ULL * 1024 * 1024);
        context = ggml_init({metadata.size(), metadata.data(), true});
        if (!context) return 13;
        weight = ggml_new_tensor_2d(context, GGML_TYPE_Q8_0, width, vocabulary);
        norm = ggml_new_tensor_1d(context, GGML_TYPE_F32, width);
        hidden = ggml_new_tensor_1d(context, GGML_TYPE_F32, width);
        auto * normalized = ggml_mul(
            context, ggml_rms_norm(context, hidden, 1.0e-5f), norm);
        logits = ggml_mul_mat(context, weight, normalized);
        graph = ggml_new_graph_custom(context, GGML_DEFAULT_GRAPH_SIZE, false);
        ggml_build_forward_expand(graph, logits);
        for (int node = 0; node < ggml_graph_n_nodes(graph); ++node)
            if (!ggml_backend_dev_supports_op(device, ggml_graph_node(graph, node)))
                return 14;
        buffer = ggml_backend_alloc_ctx_tensors(context, backend);
        if (!buffer) return 15;
        ggml_backend_tensor_set(weight, weight_values, 0, ggml_nbytes(weight));
        ggml_backend_tensor_set(norm, norm_values, 0, ggml_nbytes(norm));
        ggml_backend_synchronize(backend);
        source_weight = weight_values;
        ready = true;
        return 0;
    }
};

PersistentOutputMetal state;

}  // namespace

extern "C" void aion_gptoss_output_shutdown() { state.release(); }

extern "C" int aion_gptoss_output(
        const void * weight_values, const float * norm_values,
        const float * hidden_values, float * logit_values, int,
        int * token_id, double * logit_checksum, double * elapsed_ms) {
    if (!weight_values || !norm_values || !hidden_values || !logit_values ||
        !token_id || !logit_checksum || !elapsed_ms) return 1;
    if (!state.ready) {
        const int status = state.initialise(weight_values, norm_values);
        if (status) return status;
    }
    // A changed backing allocation would invalidate the persistent upload.
    if (state.source_weight != weight_values) return 16;
    const auto begin = std::chrono::steady_clock::now();
    ggml_backend_tensor_set(
        state.hidden, hidden_values, 0, PersistentOutputMetal::width * sizeof(float));
    if (ggml_backend_graph_compute(state.backend, state.graph) != GGML_STATUS_SUCCESS)
        return 17;
    ggml_backend_synchronize(state.backend);
    ggml_backend_tensor_get(
        state.logits, logit_values, 0,
        PersistentOutputMetal::vocabulary * sizeof(float));
    *elapsed_ms = std::chrono::duration<double, std::milli>(
        std::chrono::steady_clock::now() - begin).count();
    int best = 0;
    double checksum = 0.0;
    for (int index = 0; index < PersistentOutputMetal::vocabulary; ++index) {
        if (!std::isfinite(logit_values[index])) return 18;
        if (logit_values[index] > logit_values[best]) best = index;
        checksum += logit_values[index];
    }
    *token_id = best;
    *logit_checksum = checksum;
    return 0;
}
