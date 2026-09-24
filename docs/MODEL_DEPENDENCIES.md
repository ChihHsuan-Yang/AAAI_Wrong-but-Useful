# Upstream model dependency card

**This is not a model release.** No checkpoint, adapter, LoRA, or fine-tune was
produced for this paper, and none is distributed. This document describes the
*upstream* models the experiments depended on, so a reader can configure an
equivalent setup and audit what actually ran.

> This work does not release a paper-specific trained model. Experiments use
> openly available upstream model families through inference endpoints.

## The two upstream families

| Role in the paper | Canonical identifier | Referred to as |
|---|---|---|
| Primary actor | `openai/gpt-oss-120b` | OSS |
| Secondary actor | `google/gemma-4-31B-it` | Gemma |
| Evaluator, both arms | `openai/gpt-oss-120b` | OSS evaluator |

Both were reached over an OpenAI-compatible `/chat/completions` surface. Neither
was modified. Weights were never downloaded, held, or redistributed as part of
this work.

## Actor vs evaluator: why the split is structural

The paper's design is explicit: *"Both gpt-oss-120b and gemma-4-31B-it model
families use a separate gpt-oss-120b evaluator. The evaluator sees only the
submitted answer and an evaluator-only ground truth."*

Three of the four roles -- recruiter, hypothesizer, integrator -- belong to the
**actor family** and change together between the primary and secondary arms. The
**evaluator stays OSS in both arms**. In the Gemma arm, actor and evaluator are
therefore necessarily different models; a configuration that cannot express that
cannot run the Gemma arm at all.

This is why `src/dhd/config.py` refuses to bind two differently-declared model
slots to one identifier, and why `DHD_ACTOR_*` deliberately does **not** cover
the evaluator. It is also why the published ancillary artifact, which sent one
`MODEL_API_MODEL` for every role, could not enact the paper's protocol for the
secondary arm -- a defect this repository fixes and tests against.

## Decoding settings, per role

Read directly from `configs/paper/dhd_config.yaml` and
`configs/paper/dhd_config_secondary_actor.yaml`. Both files declare the same
values; only the actor model slot differs between them.

| Role | Temperature | Max tokens | Notes |
|---|---|---|---|
| Recruiter | 0.0 | 2048 | Assigns the five reasoning roles. |
| Hypothesizer (x5) | 0.7 | 4096 | The only sampled role -- five independent messages per problem come from here. |
| Integrator | 0.0 | 4096 | The measurement subject: re-run with each message available or hidden. |
| Evaluator | 0.0 | 4096 | Sees the submitted answer and an evaluator-only reference; emits `Correctness: 0|1`. |

The configs are the authority. `python scripts/dry_run.py` prints the values
actually in force for your run, including any `DHD_TEMPERATURE_OVERRIDE` or
`DHD_MAX_TOKENS_OVERRIDE` you set -- and setting either means you are no longer
running the paper's decoding.

## No weight-revision hash is available

The hosted endpoints used for the paper **did not expose weight-revision
hashes**. There is therefore no pin that would let anyone -- including the
authors -- assert that a future run hits the same weights. Naming the family is
the strongest available claim, and this card does not dress it up as more.

Practically: a provider can update a served model under an unchanged identifier.
If your numbers drift from the paper's, an upstream revision is among the
explanations that cannot be ruled out.

## Limits on determinism

Even at `temperature=0`, byte-identical text across deployments is not
achievable here, for reasons that stack:

1. **No seed parameter.** The OpenAI-compatible surface used exposes none, so
   the sampler cannot be fixed from the client.
2. **No revision pin.** See above.
3. **Batching and kernel nondeterminism.** Server-side batching, tensor
   parallelism, and reduction order make greedy decoding only approximately
   deterministic on most serving stacks.
4. **Independent evaluator calls.** Correctness comes from a second model call,
   which carries its own variance -- verdicts can differ on byte-identical
   inputs.

What *is* deterministic and is checked in CI: figure and table regeneration from
the bundled CSVs, and the seeded bootstraps in label aggregation
(`trajectory_value_label`, seed 20260717 by default). That is the scope of the
exact-value claim; see the README's Level 1.

## How to configure your own endpoint

Any server exposing `POST {base}/chat/completions` with the usual `model`,
`messages`, `temperature`, `max_tokens` fields works -- vLLM, llama.cpp's
server, SGLang, TGI's OpenAI shim, or a commercial API.

```bash
cp .env.example .env
# minimum: an actor endpoint+model, and a SEPARATE evaluator endpoint+model
set -a && . ./.env && set +a
python scripts/dry_run.py
```

A single local server can host both roles: point both base URLs at it and give
the two roles different `model` values it serves. What is not allowed is one
model identifier for both -- that is the collapse the config layer rejects.

## How to dry-run

```bash
python scripts/dry_run.py            # human-readable
python scripts/dry_run.py --json     # machine-readable
```

Makes **no network call**. Prints per role: provider, sanitized endpoint (host
and port only -- userinfo, path, and query are stripped, so a credential
embedded in a URL cannot leak), the declared model slot, the resolved
identifier and which environment variable supplied it, the identifier that will
be emitted, temperature, max tokens, and whether a credential is present and
from which variable -- never its value. Also prints seed behaviour, config
SHA-256, code commit, benchmark, requested sample ids, expected role-call count,
and the output path.

Exit code 2 means the configuration contradicts itself; the message says how.

## How to confirm which model actually ran

Do not trust a filename, a CLI flag, a job name, or an output directory. A model
name in any of those is not evidence that the model ran.

After a run, read the emitted identity out of the run's own output:

```bash
python -c "import json,sys; d=json.load(open(sys.argv[1]))['model_identity']; \
print(json.dumps({'emitted': d['emitted_models_by_role'], \
'matches_configured': d['emitted_matches_configured'], \
'config_sha256': d['config_sha256'], 'code_commit': d['code_commit']}, indent=2))" \
  outputs/smoke_output/smoke_results.json
```

`emitted_models_by_role` is recorded from the `model` field of the requests that
were actually issued, grouped by role. `RUN_META.json` carries the same block for
a masking run. If emitted differs from configured, the run **exits non-zero** and
says so; it does not quietly record a mismatch.

## Upstream licensing

Both families are distributed by their upstream publishers under their own
terms, which govern your use of them. This repository's MIT license covers the
code here and nothing about the models. No model weights are redistributed.
