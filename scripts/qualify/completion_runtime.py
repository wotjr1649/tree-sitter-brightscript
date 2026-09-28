"""Unadopted completion-checkpoint experiment on exact upstream 0.27.0 bytes.

This does not change the stock runtime manifest or release qualification.
The caller verifies the complete runtime manifest before compiling a copy.
"""
import hashlib

BASE_SHA256 = "97a49276242294bc1b1a22908671a202f92d2a213a872edbe467a9e121822615"
CANDIDATE_SHA256 = "db59f31c13e4cface79d86e5cf890f9b85390cd4db55ed1ff09c38b33b8e30fd"
VARIANT = "0.27.0+completion-checkpoint-candidate1"

ELIGIBILITY = """// Restrict the new cancellation boundary to completed alternatives. Resume
// must not advance an active/paused alternative before disposing of the stack.
static bool ts_parser__can_cancel_completion(TSParser *self) {
  return self->finished_tree.ptr &&
    ts_stack_halted_version_count(self->stack) == ts_stack_version_count(self->stack);
}

"""
CHECKPOINT = """    if (ts_parser__can_cancel_completion(self)) {
      const uint32_t checkpoint_position = self->lexer.current_position.bytes;
      if (!ts_parser__check_progress(self, NULL, &checkpoint_position, OP_COUNT_PER_PARSER_CALLBACK_CHECK)) {
        return NULL;
      }
    }
"""
CONDENSE = "    unsigned min_error_cost = ts_parser__condense_stack(self);"


def candidate_bytes(original):
    if hashlib.sha256(original).hexdigest() != BASE_SHA256:
        raise ValueError("completion experiment requires the exact stock 0.27.0 parser")
    source = original.decode("utf-8")
    replacements = (
        ("static bool ts_parser_has_outstanding_parse(TSParser *self) {",
         ELIGIBILITY + "static bool ts_parser_has_outstanding_parse(TSParser *self) {"),
        ("  return (\n    self->canceled_balancing ||",
         "  return (\n    self->finished_tree.ptr ||\n    self->canceled_balancing ||"),
        (CONDENSE, "    // Acceptance and stack disposal can each be substantial work. Honor\n"
         "    // cancellation between them while retaining the finished tree for resume.\n"
         + CHECKPOINT + CONDENSE + "\n" + CHECKPOINT.rstrip()),
    )
    for before, after in replacements:
        if source.count(before) != 1:
            raise ValueError("completion experiment source anchor differs")
        source = source.replace(before, after)
    result = source.encode("utf-8")
    if hashlib.sha256(result).hexdigest() != CANDIDATE_SHA256:
        raise ValueError("completion experiment output identity differs")
    return result


def controls_bytes(candidate):
    if hashlib.sha256(candidate).hexdigest() != CANDIDATE_SHA256:
        raise ValueError("controls require the exact uninstrumented candidate")
    source = candidate.decode("utf-8")
    if source.count(CHECKPOINT.rstrip()) != 2:
        raise ValueError("completion checkpoint registration differs")
    for phase in (1, 2):
        source = source.replace(CHECKPOINT.rstrip(), CHECKPOINT.rstrip().replace(
            "      const uint32_t", f"      control_checkpoint_phase = {phase};\n      const uint32_t"), 1)
    result = source.encode("utf-8")
    stripped = result
    for phase in (1, 2):
        stripped = stripped.replace(f"      control_checkpoint_phase = {phase};\n".encode(), b"")
    if stripped != candidate:
        raise ValueError("controls instrumentation changed candidate behavior")
    return result
