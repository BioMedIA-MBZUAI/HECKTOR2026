## Submitting to the HECKTOR 2026 Challenge

Assuming you have a verified Grand Challenge account and have registered for the challenge, you need two steps: upload your algorithm container, then submit it to a phase.

### 1 — Upload your algorithm

> **Important:** Unlike HECKTOR 2025 (which had three separate task algorithms), HECKTOR 2026 uses a **single algorithm** that outputs all three subtask results (segmentation, TN staging, and prognosis).

- Navigate to the [Grand Challenge algorithms page](https://grand-challenge.org/algorithms/) and click **"+ Add new algorithm"**.
- Select the appropriate challenge phase from the drop-down list.
- Enter a meaningful **Title** and **Job Description**.

> **Note:** You can only create a limited number of algorithms. Avoid titles with "test" or "debug". You only need to create **1 algorithm per phase** — you can upload new container images as you improve your model.

- After creating the algorithm, go to the **Containers** tab and upload your `.tar.gz` file (produced by `./do_save.sh`).
- The algorithm is ready when the status badge changes to **Active**.

### 2 — Submit your algorithm

- Log in to the challenge portal (TBA once the 2026 site is live).
- Navigate to the phase you want to submit to (Sanity Check, Validation, or Testing).
- Select your uploaded algorithm from the drop-down and click **Save**.

### Phases

| Phase | Cases | Submissions |
|---|---|---|
| **Sanity Check** | 3 images | Unlimited — verifies your container runs without errors |
| **Validation (Phase 1)** | ~50 images | 2 submissions — results published on leaderboard |
| **Testing (Phase 2)** | ~500 images | 1 submission — official ranking |

> Participants will not receive detailed feedback during the testing phase, only error notifications.
