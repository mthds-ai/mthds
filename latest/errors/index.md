# Error Codes

Every code of the MTHDS core error registry has a page here, at the URL a problem's `type` names: `https://mthds.ai/errors/<code>`. Each page says what its code means, who must act and what to do, and gives the code's steps, parameters and templates. The [Error Registry](../spec/error-registry.md) page describes the registry itself, and the [HTTP Runner Protocol](../spec/protocol.md#errors) how a problem document carries a code.

These pages are generated from the registry's data, which is published with every release of the standard as [`mthds-error-registry.json`](../spec/openapi/mthds-error-registry.json). This is version `8.0.1` of the registry.

## Extension prefixes

A code that is not a core code starts with a registered prefix, and its page is published by the prefix's owner, under the base URL the prefix is registered with.

| Prefix | Owner | Base URL |
|---|---|---|
| `pipelex.` | Pipelex | <https://docs.pipelex.com/errors> |

## request

The HTTP request itself, before any run.

| Code | Title | Domain | Retry | Status |
|---|---|---|---|---|
| [`request.malformed`](request/malformed.md) | The request body cannot be parsed | `input` | `no` | `422` |
| [`request.invalid`](request/invalid.md) | The request does not match the route's schema | `input` | `no` | `422` |
| [`request.too_large`](request/too_large.md) | The request exceeds a size limit | `input` | `no` | `413` |
| [`request.not_found`](request/not_found.md) | No such route | `input` | `no` | `404` |
| [`request.method_not_allowed`](request/method_not_allowed.md) | The route does not accept this HTTP method | `input` | `no` | `405` |
| [`request.unsupported`](request/unsupported.md) | The request uses a form this runtime does not accept | `input` | `no` | `422` |
| [`request.idempotency_conflict`](request/idempotency_conflict.md) | The idempotency key was used for a different request | `input` | `no` | `409` |
| [`request.idempotency_key_in_use`](request/idempotency_key_in_use.md) | A request under this idempotency key is still running | `runtime` | `yes` | `409` |
| [`request.already_executed`](request/already_executed.md) | The request already ran and its answer is not kept | `input` | `no` | `409` |
| [`request.pipe_not_found`](request/pipe_not_found.md) | The selected pipe is not in the method | `input` | `no` | `422` |
| [`request.pipe_ambiguous`](request/pipe_ambiguous.md) | The pipe selection matches several pipes | `input` | `no` | `422` |
| [`request.pipe_unspecified`](request/pipe_unspecified.md) | No pipe is selected | `input` | `no` | `422` |
| [`request.blobs_missing`](request/blobs_missing.md) | The runner does not hold some files sent by hash | `input` | `no` | `422` |

## auth

Credentials and permissions.

| Code | Title | Domain | Retry | Status |
|---|---|---|---|---|
| [`auth.missing_credential`](auth/missing_credential.md) | No credential was sent | `account` | `no` | `401` |
| [`auth.invalid_credential`](auth/invalid_credential.md) | The credential was refused | `account` | `no` | `401` |
| [`auth.credential_expired`](auth/credential_expired.md) | The credential has expired | `account` | `no` | `401` |
| [`auth.forbidden`](auth/forbidden.md) | The credential does not permit this | `account` | `no` | `403` |

## account

The account's limits.

| Code | Title | Domain | Retry | Status |
|---|---|---|---|---|
| [`account.rate_limited`](account/rate_limited.md) | The account is over its request rate | `account` | `yes` | `429` |
| [`account.quota_exhausted`](account/quota_exhausted.md) | The account's quota is used up | `account` | `no` | `429` |

## input

A run's inputs.

| Code | Title | Domain | Retry | Status |
|---|---|---|---|---|
| [`input.missing`](input/missing.md) | A required input is missing | `input` | `no` | `422` |
| [`input.unexpected`](input/unexpected.md) | An input the method does not declare | `input` | `no` | `422` |
| [`input.wrong_concept`](input/wrong_concept.md) | An input is not of the kind the method declares | `input` | `no` | `422` |
| [`input.wrong_multiplicity`](input/wrong_multiplicity.md) | An input has the wrong form or the wrong number of items | `input` | `no` | `422` |
| [`input.invalid`](input/invalid.md) | An input does not have the structure the method declares | `input` | `no` | `422` |
| [`input.file_unreadable`](input/file_unreadable.md) | An input file cannot be read | `input` | `no` | `422` |
| [`input.file_type_unsupported`](input/file_type_unsupported.md) | An input file's type is not supported here | `input` | `no` | `422` |
| [`input.too_large`](input/too_large.md) | An input exceeds a size limit | `input` | `no` | `422` |
| [`input.reference_not_found`](input/reference_not_found.md) | An input refers to something that does not exist | `input` | `no` | `422` |
| [`input.url_unreachable`](input/url_unreachable.md) | An input's URL could not be fetched | `input` | `yes` | `422` |

## method

The method as written, the validation vocabulary included.

| Code | Title | Domain | Retry | Status |
|---|---|---|---|---|
| [`method.invalid`](method/invalid.md) | The method does not validate | `method` | `no` | `422` |
| [`method.syntax`](method/syntax.md) | The method does not parse | `method` | `no` | `422` |
| [`method.schema_violation`](method/schema_violation.md) | The method breaks a rule of the language | `method` | `no` | `422` |
| [`method.not_found`](method/not_found.md) | No method at this address | `input` | `no` | `404` |
| [`method.ambiguous`](method/ambiguous.md) | The method address matches several methods | `input` | `no` | `422` |
| [`method.fetch_failed`](method/fetch_failed.md) | The method could not be fetched | `runtime` | `yes` | `502` |
| [`method.package_invalid`](method/package_invalid.md) | The method's package breaks a package rule | `method` | `no` | `422` |
| [`method.dependency_missing`](method/dependency_missing.md) | A dependency of the method is not available | `method` | `no` | `422` |
| [`method.dependency_invalid`](method/dependency_invalid.md) | A dependency of the method does not load | `method` | `no` | `422` |
| [`method.resource_missing`](method/resource_missing.md) | A file the method refers to is not in its tree | `method` | `no` | `422` |
| [`method.concept_unresolved`](method/concept_unresolved.md) | The method names a concept no library declares | `method` | `no` | `422` |
| [`method.pipe_unresolved`](method/pipe_unresolved.md) | The method names a pipe that does not exist | `method` | `no` | `422` |
| [`method.pipe_not_exported`](method/pipe_not_exported.md) | The method calls a pipe its dependency does not export | `method` | `no` | `422` |
| [`method.ref_ambiguous`](method/ref_ambiguous.md) | A reference matches several declarations | `method` | `no` | `422` |
| [`method.name_conflict`](method/name_conflict.md) | A name is declared twice or collides with a reserved one | `method` | `no` | `422` |
| [`method.cycle`](method/cycle.md) | Declarations form a cycle | `method` | `no` | `422` |
| [`method.identifier_invalid`](method/identifier_invalid.md) | A name is not a valid identifier | `method` | `no` | `422` |
| [`method.pipe_type_invalid`](method/pipe_type_invalid.md) | A pipe's type is missing, unknown or retired | `method` | `no` | `422` |
| [`method.signature_mismatch`](method/signature_mismatch.md) | A pipe differs from its signature | `method` | `no` | `422` |
| [`method.not_runnable`](method/not_runnable.md) | The method still holds pipe signatures | `method` | `no` | `422` |
| [`method.input_undeclared`](method/input_undeclared.md) | A pipe reads an input it does not declare | `method` | `no` | `422` |
| [`method.input_unused`](method/input_unused.md) | A pipe declares an input it never reads | `method` | `no` | `422` |
| [`method.input_concept_mismatch`](method/input_concept_mismatch.md) | A pipe's input concept does not fit its use | `method` | `no` | `422` |
| [`method.output_concept_mismatch`](method/output_concept_mismatch.md) | A pipe's output concept does not fit | `method` | `no` | `422` |
| [`method.output_multiplicity_mismatch`](method/output_multiplicity_mismatch.md) | A pipe's declared multiplicity does not fit its use | `method` | `no` | `422` |
| [`method.wiring_invalid`](method/wiring_invalid.md) | A pipe's wiring does not give it what it reads | `method` | `no` | `422` |
| [`method.field_path_unresolved`](method/field_path_unresolved.md) | A path names a field its concept does not have | `method` | `no` | `422` |
| [`method.binding_step_invalid`](method/binding_step_invalid.md) | A binding step is malformed | `method` | `no` | `422` |
| [`method.optional_marker_invalid`](method/optional_marker_invalid.md) | An optional marker is misplaced | `method` | `no` | `422` |
| [`method.optional_unhandled`](method/optional_unhandled.md) | An optional value reaches a place that needs a required one | `method` | `no` | `422` |
| [`method.template_invalid`](method/template_invalid.md) | A template in the method is invalid | `method` | `no` | `422` |
| [`method.template_private_name`](method/template_private_name.md) | A template reads a name reserved to the runtime | `method` | `no` | `422` |
| [`method.function_invalid`](method/function_invalid.md) | A function the method declares cannot be used | `method` | `no` | `422` |
| [`method.concept_invalid`](method/concept_invalid.md) | A concept's structure cannot be built or described | `method` | `no` | `422` |
| [`method.model_setting_invalid`](method/model_setting_invalid.md) | A model setting in the method is invalid | `method` | `no` | `422` |
| [`method.mock_unsatisfiable`](method/mock_unsatisfiable.md) | The dry run cannot mock an output concept | `method` | `no` | `422` |
| [`method.changed_concurrently`](method/changed_concurrently.md) | A method file changed while it was being fixed | `runtime` | `yes` | `409` |
| [`method.hint_invalid`](method/hint_invalid.md) | A hint is not understood | `method` | `no` | none (warning) |
| [`method.input_presence_vacuous`](method/input_presence_vacuous.md) | A presence check always holds | `method` | `no` | none (warning) |
| [`method.optional_force_redundant`](method/optional_force_redundant.md) | An optional force is redundant | `method` | `no` | none (warning) |

## pipe

A pipe failing at run time because of what the method does.

| Code | Title | Domain | Retry | Status |
|---|---|---|---|---|
| [`pipe.output_multiplicity`](pipe/output_multiplicity.md) | A step produced a list instead of one result, or the reverse | `method` | `no` | `422` |
| [`pipe.output_invalid`](pipe/output_invalid.md) | A step's result does not have the structure the method declares | `method` | `no` | `422` |
| [`pipe.function_raised`](pipe/function_raised.md) | The method's function failed | `method` | `no` | `422` |
| [`pipe.function_timed_out`](pipe/function_timed_out.md) | The method's function ran past its time limit | `method` | `no` | `422` |
| [`pipe.template_render_failed`](pipe/template_render_failed.md) | A template in the method could not be filled in | `method` | `no` | `422` |
| [`pipe.template_budget_exceeded`](pipe/template_budget_exceeded.md) | A template in the method tried to do more than it may | `method` | `no` | `422` |
| [`pipe.condition_unmatched`](pipe/condition_unmatched.md) | A condition matched no outcome | `method` | `no` | `422` |
| [`pipe.condition_refused`](pipe/condition_refused.md) | The method refused these inputs | `input` | `no` | `422` |
| [`pipe.binding_failed`](pipe/binding_failed.md) | A step could not find a field in the value it reads | `method` | `no` | `422` |
| [`pipe.input_unresolved`](pipe/input_unresolved.md) | A step could not read a value it needs | `method` | `no` | `422` |
| [`pipe.forced_input_absent`](pipe/forced_input_absent.md) | A value the method counts on was missing | `method` | `no` | `422` |
| [`pipe.prompt_empty`](pipe/prompt_empty.md) | A step's prompt came out empty | `input` | `no` | `422` |
| [`pipe.stack_overflow`](pipe/stack_overflow.md) | The run nested its steps deeper than the limit | `method` | `no` | `422` |

## model

The model a step names.

| Code | Title | Domain | Retry | Status |
|---|---|---|---|---|
| [`model.unknown`](model/unknown.md) | The method names a model that does not exist | `method` | `no` | `422` |
| [`model.unavailable`](model/unavailable.md) | This deployment serves no backend for the model | `operator` | `no` | `501` |
| [`model.unspecified`](model/unspecified.md) | No model is named for this step | `method` | `no` | `422` |
| [`model.capability_unsupported`](model/capability_unsupported.md) | The model cannot do what the step asks | `method` | `no` | `422` |
| [`model.context_exceeded`](model/context_exceeded.md) | The inputs exceed what the model can read | `input` | `no` | `422` |
| [`model.output_truncated`](model/output_truncated.md) | The model's answer was cut off at the method's length limit | `method` | `no` | `422` |
| [`model.output_schema_mismatch`](model/output_schema_mismatch.md) | The model's answer did not have the expected structure | `runtime` | `yes` | `502` |
| [`model.content_refused`](model/content_refused.md) | The provider refused the content | `input` | `no` | `422` |
| [`model.no_result`](model/no_result.md) | The model found nothing for this request | `input` | `no` | `422` |

## provider

The inference provider behind a model.

| Code | Title | Domain | Retry | Status |
|---|---|---|---|---|
| [`provider.rate_limited`](provider/rate_limited.md) | The provider is rate limiting this deployment | `runtime` | `yes` | `429` |
| [`provider.unavailable`](provider/unavailable.md) | The provider is unavailable | `runtime` | `yes` | `502` |
| [`provider.timeout`](provider/timeout.md) | The provider did not answer in time | `runtime` | `yes` | `504` |
| [`provider.failed`](provider/failed.md) | The provider failed | `runtime` | `yes` | `502` |
| [`provider.response_invalid`](provider/response_invalid.md) | The provider's answer could not be used | `runtime` | `yes` | `502` |
| [`provider.credential_refused`](provider/credential_refused.md) | The provider refused this deployment's credential | `operator` | `no` | `502` |
| [`provider.quota_exhausted`](provider/quota_exhausted.md) | This deployment's provider account is out of quota | `operator` | `no` | `502` |
| [`provider.outcome_unknown`](provider/outcome_unknown.md) | The provider call may have taken effect | `runtime` | `yes` | `502` |

## run

A run's lifecycle and its reads.

| Code | Title | Domain | Retry | Status |
|---|---|---|---|---|
| [`run.not_found`](run/not_found.md) | No such run | `input` | `no` | `404` |
| [`run.failed`](run/failed.md) | The run did not succeed | `runtime` | `no` | `409` |
| [`run.not_finished`](run/not_finished.md) | The run has not finished | `runtime` | `yes` | `409` |
| [`run.cancelled`](run/cancelled.md) | The run was cancelled by its caller | `input` | `yes` | `409` |
| [`run.timed_out`](run/timed_out.md) | The run passed its time limit | `method` | `no` | `422` |
| [`run.lost`](run/lost.md) | The run's outcome is lost | `runtime` | `outcome_unknown` | `500` |
| [`run.outcome_unknown`](run/outcome_unknown.md) | The runtime cannot tell whether the run started or finished | `runtime` | `outcome_unknown` | `502` |
| [`run.already_ended`](run/already_ended.md) | The run has already ended | `input` | `no` | `409` |
| [`run.answer_not_kept`](run/answer_not_kept.md) | The run's answer was not kept | `input` | `no` | `409` |
| [`run.results_not_stored`](run/results_not_stored.md) | The run's results were not stored | `input` | `no` | `404` |
| [`run.terminated`](run/terminated.md) | The run was stopped by an operator or an erasure | `operator` | `no` | `409` |

## security

Refusals made for safety. An implementation may also record each one as a security event.

| Code | Title | Domain | Retry | Status |
|---|---|---|---|---|
| [`security.input_url_refused`](security/input_url_refused.md) | A URL in the request was refused | `input` | `no` | `422` |
| [`security.method_url_refused`](security/method_url_refused.md) | A URL the method names was refused | `method` | `no` | `422` |
| [`security.provider_url_refused`](security/provider_url_refused.md) | A URL a provider returned was refused | `runtime` | `no` | `502` |
| [`security.input_path_refused`](security/input_path_refused.md) | A path the caller supplied was refused | `input` | `no` | `422` |
| [`security.method_path_refused`](security/method_path_refused.md) | A path the method names was refused | `method` | `no` | `422` |
| [`security.template_refused`](security/template_refused.md) | A template in the method reached for something it may not use | `method` | `no` | `422` |
| [`security.schema_refused`](security/schema_refused.md) | The method declares an output structure the runtime refuses | `method` | `no` | `422` |
| [`security.integrity_mismatch`](security/integrity_mismatch.md) | A dependency's content differs from its lock | `method` | `no` | `422` |

## runtime

The runtime itself.

| Code | Title | Domain | Retry | Status |
|---|---|---|---|---|
| [`runtime.unexpected`](runtime/unexpected.md) | An unexpected error occurred | `runtime` | `no` | `500` |
| [`runtime.misconfigured`](runtime/misconfigured.md) | The runtime is misconfigured | `operator` | `no` | `500` |
| [`runtime.unavailable`](runtime/unavailable.md) | The runtime or a service it depends on is unavailable | `runtime` | `yes` | `503` |
| [`runtime.unsupported`](runtime/unsupported.md) | This runtime cannot do what was asked | `operator` | `no` | `501` |

## client

What a client detects itself, and never receives as a response body.

| Code | Title | Domain | Retry | Status |
|---|---|---|---|---|
| [`client.unreachable`](client/unreachable.md) | The runtime could not be reached | `runtime` | `yes` | none (client) |
| [`client.timeout`](client/timeout.md) | The runtime did not answer in time | `runtime` | `yes` | none (client) |
| [`client.response_unreadable`](client/response_unreadable.md) | The runtime's answer could not be read | `runtime` | `no` | none (client) |
| [`client.outcome_unknown`](client/outcome_unknown.md) | The call may have created a run | `runtime` | `outcome_unknown` | none (client) |
| [`client.follow_failed`](client/follow_failed.md) | Following a started run stopped | `runtime` | `outcome_unknown` | none (client) |
| [`client.not_configured`](client/not_configured.md) | The client has no usable configuration | `input` | `no` | none (client) |
| [`client.argument_invalid`](client/argument_invalid.md) | An argument was refused before sending | `input` | `no` | none (client) |
| [`client.file_unreadable`](client/file_unreadable.md) | A local file cannot be read | `input` | `no` | none (client) |
| [`client.write_failed`](client/write_failed.md) | A local file could not be written | `input` | `no` | none (client) |
| [`client.target_exists`](client/target_exists.md) | The target already exists | `input` | `no` | none (client) |
| [`client.workspace_busy`](client/workspace_busy.md) | Local files changed underneath the client | `runtime` | `yes` | none (client) |
| [`client.output_mismatch`](client/output_mismatch.md) | An output does not match the generated types | `input` | `no` | none (client) |
| [`client.link_refused`](client/link_refused.md) | A download link was refused | `operator` | `no` | none (client) |
| [`client.download_limit_exceeded`](client/download_limit_exceeded.md) | A download passed the client's limit | `input` | `no` | none (client) |
| [`client.aborted`](client/aborted.md) | The call was stopped by the caller | `input` | `yes` | none (client) |
| [`client.tool_missing`](client/tool_missing.md) | A local tool the client needs is missing | `input` | `no` | none (client) |
| [`client.tool_outdated`](client/tool_outdated.md) | A local tool is too old | `input` | `no` | none (client) |
