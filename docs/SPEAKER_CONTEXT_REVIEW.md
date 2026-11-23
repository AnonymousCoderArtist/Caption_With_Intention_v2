# Speaker uncertainty with neighbouring context, approved review

23 November 2026. User approved publication at19:17IST.

The editor already has speaker review flags/filter,reasons,listen-to-turn,next unchecked turn,manual assignment/name editing and mark-checked. It does not have a calibrated diarization identity-confidence score. ASR text confidence and diarization timing coverage must not be sold as that score.

This round makes the low-certainty review path easier without any face model:

- Show speaker review ranges is OFF by default. Checking it displays only flagged intervals plus1.5seconds either side,clamped to source duration;overlapping intervals merge.
- Watch buttons play those context windows and stop at their end. The selected-caption inspector also offers Watch nearby context when flagged.
- Flags come from missing attribution,turns shorter than0.4seconds,supplied review reasons/required flags,and timing coverage below70%. The latter is a review policy,not a model confidence cutoff. A low ASR text score alone does not trigger a speaker flag.
- Marking checked removes that turn from the generated review ranges. Reopen puts it back. No speaker/color changes automatically. No face model,no uploads,no face data stored.

98frontend tests,production build/full browser acceptance pass. Focused real18s portrait journey verifies opt-in range display and actual source playback. Backend unchanged since712passed/9skipped.

## Restricting future face hints to these windows

This is the right boundary for an optional future visual suggestion pass,but it does not fix failed face tracking or establish who is speaking. Padding helps gather context and avoids scanning unrelated confident stretches. It must remain off by default,no persistent face templates,and suggest/flag only after human confirmation.

Savings depend on flagged coverage. On the current uncertain45.038s project,padded/merged ranges cover44.308s,98.4%. On the18s crop they cover17.13s,95.2%. Therefore this gate barely reduces work on these difficult clips. Do not claim a speedup from selective analysis here. On genuinely sparse flags it could reduce work,which needs measurement on such a project.

Visual research still does not support a shipped automatic assignment:YuNet improves face-detection coverage over MediaPipe on the difficult clip,but coverage is not attribution accuracy;the provisional CPU audio-visual diagnostic did not establish usable active-speaker output. No independently labeled speaking-face truth exists,so no speaker-accuracy percentage is claimed. Continue with manual review now. Further visual research needs labeled intervals,shot-aware anonymous tracks,a measured CPU runtime and precision/abstention/wrong-color evaluation. No face model is wired into the editor in this round.
