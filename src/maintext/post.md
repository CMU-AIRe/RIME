![](assets/figures/fig01_teaser.gif "*Figure 1.* **Our approach trains a model to act and write memories over a stream of related tasks.** The model alternates between solving a task (ACT) and writing a memory (WRITE) that conditions its rollout on the next task. The goal is to produce memories that make future tasks easier to solve, maximizing cumulative performance over all tasks appearing across the stream of tasks. Effective memories should enable successful performance on as many subsequent tasks as possible, as illustrated by larger radii of the red circles in the right panel. We train a single model with reinforcement learning (RL) to be effective at both acting on the task stream and writing effective memories.")

LLM agents increasingly tackle sequences of related tasks, often situated within the same environment. A coding agent may implement a series of changes to the same codebase, while an automated scientist may run experiments that build on earlier results. In such cases, the agent should benefit from what it has already learned. This problem is a variant of continual learning, and indeed, a benchmark we study in this work is Continual Learning Bench. Earlier work has explored this through [reusable workflows](https://arxiv.org/abs/2409.07429), [continual adaptation of agent harnesses](https://arxiv.org/abs/2605.09998), and [training agents to use text notes](https://engram.com/blog/learning-in-a-world-of-notes). In this work, we study how we can train models to write good memories from their past experience to help future tasks.

A common approach to writing memories is to prompt an LLM to summarize or “compact” its experience, using instructions or templates that specify what to retain. For example, modern coding agents append summaries of new experiences to a `MEMORY.md` file. But can fixed instructions reliably capture what will be useful across different tasks and environments? Rather than prescribe the content and structure of memory in advance, we explore whether agents can learn effective memory-writing strategies directly from experience. As shown in Figure 1, we train a single model to take on two roles: an **actor** that solves tasks using the memories accumulated so far, and a **writer** that updates those memories after each task. We use reinforcement learning to reward the actor for solving its current task and the writer for producing memories that help on subsequent tasks.

This all sounds straightforward, but there is a catch: <strong class="md-plain">useful memories require informative experience.</strong> If the actor focuses only on finishing its current task, will it discover anything worth remembering for the next one? **Our key finding is that training the writer alone for memory writing is not enough. We also need to train the actor to explore in ways that produce useful information for future tasks.** The actor and writer also need to “keep up” with each other during training, so that the writer captures useful information and the actor learns to use it. In this blog post, we describe a simple RL approach that addresses these challenges. On the Codebase Adaptation task in [Continual Learning Bench](https://continual-learning-bench.com/), our trained **Qwen3.5-4B** model leverages its memory to more effectively and efficiently write code, performing comparably to much larger closed-source models including **GPT-5.4 and Claude Opus 4.7,** and achieves the best tradeoff in our comparison between overall performance and the improvement gain from past experience.

![](assets/figures/fig02_intro_pareto.png "*Figure 2.* **Cumulative reward and cumulative gain on Codebase Adaptation.** Cumulative reward reflects overall performance, and cumulative gain reflects the improvement from past experience. Our trained Qwen3.5-4B exceeds multiple systems on both metrics, including GPT-5.4, Claude Opus 4.7, Claude Code and Codex.")

---

## Problem Statement

We consider an agent deployed in an environment where it must solve a stream of related tasks over time. Let $x_{1:T}=(x_1,\ldots,x_T)$ be an ordered stream of tasks. For example, in the coding setting described earlier, the environment is a repository and a terminal through which edits to the repository can be made, and each $x_t$ might represent an issue in the repository to be resolved, following a fixed set of development conventions and testing procedures.

We want to train the agent to identify useful information acquired from solving earlier tasks and use it to solve later tasks more effectively. Since retaining all information is infeasible in context always, we require the agent to distill its experience into a textual **memory,** which is carried forward and made available when solving task $t$. Let $M_{t-1}$ denote the piece of natural language text that defines this memory. Solving each task then involves two operations, **acting** and memory **writing**, as shown in Figure 3.

![](assets/figures/fig03_act_write_operations.png "*Figure 3.* The two operations the agent performs on each task in the stream. Our method in the next section will alternate ACT and WRITE operations to solve a stream of related tasks.")

The objective is to produce trajectories that maximize the **sum of rewards** (or success rates) for each task in the entire task stream it obtains. For studying memory training, we will assume that the agent solves task $x_t$ given the memory $M_{t-1}$, and the resulting experience $\tau_t$ is now used to produce an updated memory $M_t$ for the next task. This forms a loop that alternates between acting (ACT) and memory writing (WRITE). At first glance, this looks much like context compaction in current agent systems, where a model summarizes its history when the context window fills up. Our focus, however, is on training this process to *improve* performance on future tasks. Prompting the writer to summarize existing information and even training the writer alone to summarize information fails to take future task success into account.  Perhaps counterintuitively, we show that training the writer even with an objective that accounts for future reward is not enough and instead the biggest gains come from the actor learning to generate more diverse, informative experience. The two ACT and WRITE roles must improve together, with the actor providing useful experience and the writer turning it into memories.

---

## RIME: RL for Memory & Exploration

We want to train a single LLM policy $\pi _{\theta}$ that serves as both **actor** and **writer**, with its role specified by the prompt (Figure 3). Mathematically, we denote the actor and writer roles as:

$$
\tau_t \sim \pi_{\theta}(\cdot\mid x_t,M_{t-1}) ~~~~\text{[ACT]} \\

\displaystyle M_t \sim \pi _{\theta}(\cdot \mid M_{t-1}, \tau_t) ~~~\text{[WRITE]}
$$

The writer can preserve, add, revise, or remove information, but has no access to future tasks. Its output $M_t$ replaces $M_{t-1}$ and conditions the next task. Across the stream, the agent repeats this ACT–WRITE loop.

To build our approach, **RIME**, we stress that these two roles depend on each other. The writer can only preserve what the actor’s trajectories contain, and the actor begins each task with the memory the writer leaves behind. A strong writer is of little use if the actor’s experience is uninformative, and a strong actor gains little from memory if the writer keeps the wrong things. If the actor and writer cannot “keep up” with each other during training, they can end up optimizing their own objectives without improving the overall ACT–WRITE loop. As we will see, this is a common failure mode when the objectives for the two roles are poorly designed (or when we do not train explicitly in the loop). We train both roles with reinforcement learning on streams of training tasks. This section develops their RL objectives step by step, starting with the most direct approach and adding components where it falls short.

### Training only the actor does not teach memory writing

The most direct approach is to train only the actor, using the task reward $r_t$, and to leave the writer as the untrained model following its prompt. This is standard [multi-turn RL](https://arxiv.org/abs/2503.09516) and is common practice in the community, including [recent work](https://engram.com/blog/learning-in-a-world-of-notes). Multi-turn RL improves how the actor solves each task, but it does not improve what is carried from one task to the next. Since memory is the only channel through which experience from earlier tasks can inform later ones, the writer must identify and retain information that will be useful beyond the current task.

Moreover, training only via task reward leaves memory writing to prompting, much as in compaction-based systems. We might prompt the model to extract useful insights or record parts of its experience for future use, as in a `MEMORY.md` file. But optimizing reward on the current task does not teach the writer which information will help on later tasks. *The first part of our method therefore explicitly trains the model for memory writing.*

### Rewarding the writer for the improvement it brings

To train the writer, we sample a group of $G$ rollouts for each training stream. All rollouts start from the empty memory and face the same task at every position. Their trajectories differ, however, so by task $t$ each rollout carries a different memory, and the sibling rollouts reach every task from different starting points (a schematic of our overall method is in Figure 4).

![](assets/figures/fig04_rime_training_stream.png "*Figure 4.* **Training on one task stream with our approach, RIME.** $G$ rollouts start from an empty memory and alternate acting (ACT) and memory writing (WRITE) on the tasks. The memory-writing reward is the difference between the mean task reward over the next $K$ tasks and the mean task reward over the previous $K$ tasks. An LLM judge compares the memory before and after each task to produce the actor's exploration reward. Rewards are normalized among rollouts at the same position, separately for ACT and WRITE. For brevity, we refer to this loop as the “ACT + WRITE” loop.")

The most direct reward for a memory $M_t$ is the average task reward on the tasks it can influence. To attribute that reward to $M_t$ itself, the rollouts being compared would have to share the same history of tasks, trajectories and memories, and differ only in $M_t$. This would require branching many continuations from every position of every rollout, which is far too costly. Without branching, the downstream reward of a sibling mixes what $M_t$ contributes with the benefit of a better starting point, and a rollout that was already doing well is rewarded no matter what it writes.

We instead use the mean reward a rollout obtained over its last $K$ tasks as a proxy for its starting point and subtract it from the mean reward over the next $K$ tasks. We call the result an ***improvement reward**:*

$$
\displaystyle R_t^{\mathrm{WRITE}} = g_t \left(\bar{r} _{t+1:t+K} - \bar{r} _{t-K+1:t}\right), \qquad t<T,
$$

where $\bar{r} _{a:b}$ is the mean task reward over tasks in positions $a$ to $b$ of the stream. The subtracted term is not a constant baseline shared across rollouts. Because the siblings in each group (Figure 4) reach position $t$ with different histories, the value of this term differs among them, so each memory is credited for the change it brings about rather than for the starting point it inherited. We discuss how to use this reward with GRPO-style RL later in this blog post. The horizon $K$ determines how far ahead a memory is credited. A short horizon credits $M_t$ only for what it does for the next few tasks and misses knowledge that pays off later. A long horizon counts tasks that are increasingly shaped by memories written after $M_t$, which blurs the credit given to $M_t$. We keep $K$ relatively short compared with the length of a stream, so that each memory receives a clear credit. That said, the value of $K$ cannot be very short: as such we will see that very short task streams during training do not enable us to learn to write memory effectively. The indicator $g_t\in\{0,1\}$ requires the memory to be well formed, which keeps degenerate outputs from collecting the downstream term.

### The actor must also be trained to explore

Training the writer alone is insufficient because memory quality depends on the experience generated by the actor. Optimizing the actor solely for reward on the current task encourages task completion, but not necessarily the discovery of information useful for future tasks. As training progresses, the actor can solve training tasks increasingly effectively using knowledge encoded in its weights, exposing the memory writer to less diverse information and potentially stalling memory improvement. When memory contributes little additional information to the next task, optimizing the actor for success on the next task gives it little incentive to use the written memory effectively. This, in turn, makes the memory writing objective noisy and hence ineffective. These effects reinforce one another, stalling progress in the ACT–WRITE loop. We observe this dynamic between acting and memory writing experimentally in Q3 (Figure 10) and show a schematic illustration of this process in Figure 5. The actor must therefore be trained for ensuring that the loop “keeps up”: both to solve the current task and to generate useful information for memories that support future tasks.

![](assets/figures/fig05_act_write_loop.png "*Figure 5.* **An illustration of the ACT–WRITE loop early, midway, and late in training.** With the task reward alone (a), the actor eventually learns to solve each task more directly, so its trajectories contain less useful information and the memory carried to later tasks offers little help. With the exploration reward added (b), the actor keeps collecting useful information throughout training, and the memory continues to support later tasks.")

The most direct approach to train the policy for acting is to also reward the actor for success on later tasks, so that its experience is valued by what it enables downstream. [CoD](http://arxiv.org/abs/2606.20002), a baseline in this post, trains its actor this way. Unfortunately even that does not help sustain this loop due to imperfect **credit assignment of future task rewards**. Between the actor’s rollout on task $t$ and a later success, lie several memory updates and rollouts. Without extensive branching, it is hard to tell which parts of the current behavior were preserved in memory and contributed to that success. Credit may instead be attributed incorrectly, making the actor’s learning signal noisy. If this signal is too weak or inconsistent, it gives the actor little guidance about which new behaviors would produce useful information, and we are back to the actor primarily optimizing for task success and memory writing becoming ineffective. Therefore, we adopt a different mechanism, an **exploration bonus**, that incentivizes collection of novel diverse experience by the actor and can be computed at each task locally.

### Rewarding the actor for what it adds to memory

We reward the actor directly for the evidence the writer can gain from its trajectory, measured by the memory update it induces. Concretely, an LLM-based $\mathrm{Judge}$ compares the memory before and after the task to produce an ***exploration reward*** $e_t$:

$$
e_t = \mathrm{Judge}(M_{t-1}, M_t) \in [0,1]
$$

$e_t$ is high when $M_t$ adds to $M_{t-1}$ or corrects something in it that was wrong, and low when the update is redundant. The score is credited to the actor's rollout on task $t$, alongside the task reward $r_t$ from the environment. While rewards of this form raise concerns around hacking, we found hacking not to be a problem as long as acting and memory writing are trained together. Conceptually, since $e_t$ is credited only to the actor, the writer has no direct incentive to change the memory merely to raise $e_t$. Experimentally, we observed the exploration score to be relatively flat through training (Figure 10 in Q3) when both the actor and writer were trained. With an untrained writer, however, we did see signs of hacking, which is perhaps expected.<br /><br />To sum up, the actor is thus rewarded both for solving the task and for leaving the memory different or richer than before. We define

$$
R^{\mathrm{ACT}}_t = r_t + \beta e_t,
$$

where $\beta$ sets the weight between the two terms. Unlike a reward on later successes, $e_t$ depends only on the update that immediately follows the trajectory, so there is no long chain of memories and actions through which credit must be assigned to compute this term.

**The exploration reward is a semantic “text-diff”.** The judge sees only the two memories. It does not see the trajectory, the task, or the state of the environment, and it has no notion of which actions are worth trying. It scores the change on four criteria: new discoveries, corrected beliefs, concrete leads for future tasks, and non-redundant change. These criteria are the same in both of our domains; only the wording that says what the environment is about differs. A trajectory that tries something new but teaches nothing leaves the memory unchanged and earns nothing, while a trajectory that reveals how the environment works changes the memory and is rewarded for it. In this sense, the exploration reward is generic and universal, and can be applied to any environment that presents a stream of tasks. It resembles a novelty bonus from standard RL, except that novelty is measured on what the agent writes down rather than on the states it visits. Novelty bonuses usually required a hand-designed state representation, and we are not aware of a generic implementation of this idea for LLMs that avoids one.

### Training and optimization

Figure 4 summarizes our overall training pipeline. For each task stream, within a group, rollout $i$ produces at position $t$ a trajectory $\tau^{(i)}_t$ with task reward $r^{(i)}_t$ and exploration reward $e^{(i)}_t$, and then a memory $M^{(i)}_t$ with improvement reward $R^{\mathrm{WRITE},(i)}_t$. Each rollout thus contributes two training samples per task. The ACT sample is the trajectory on $x_t$ given $M^{(i)}_{t-1}$, and the WRITE sample is the update that produces $M^{(i)}_t$. Since all siblings in a group tackle the same task at each position, advantages are computed among them. Every reward is normalized by subtracting its mean over the $G$ siblings at a given task position and dividing by their standard deviation. The ACT advantage is the normalized task reward plus $\beta$ times the normalized exploration reward, and the WRITE advantage is the normalized improvement reward:

$$
A^{\mathrm{ACT},(i)}_t = \hat{r}^{(i)}_t + \beta\, \hat{e}^{(i)}_t, \qquad A^{\mathrm{WRITE},(i)}_t = \hat{R}^{\mathrm{WRITE},(i)}_t
$$

Both sample types are trained with [GRPO](https://arxiv.org/pdf/2402.03300), using the asymmetric clipping of [DAPO](https://arxiv.org/abs/2503.14476) and a KL penalty toward the initial model. In our main configuration, ACT and WRITE share one set of parameters and their samples are pooled in each batch. We also experiment with a “decoupled” variant that separates parameters for acting and memory writing, but find it less effective than shared-parameter training, which we refer to as “co-training”.

### Desiderata for constructing training task streams

So far, we have described our approach, but how should we construct task streams for training? Indeed, we have seen numerous times that the extent of improvement from running RL on LLMs can differ drastically across datasets, for instance in whether RL mainly [sharpens](https://arxiv.org/abs/2504.13837) what the base model can already do or [discovers](https://pinnate-flare-8f3.notion.site/Sharpening-or-Discovery-RL-or-Meta-RL-How-RL-Improves-LLM-Reasoning-20628c119540805cac48e8492638d88e) new behaviors. So how should we construct these task streams in practice?

To answer this, first note that memory use can only be meaningfully reinforced when tasks are related, such that knowledge gained on earlier tasks helps solve later ones. We encourage this by sampling segments of consecutive tasks from the same environment during training.

Second, we note that these segments must also be sufficiently long: with only a few tasks in a stream, there is little accumulation or buildup of useful memory, and each memory is evaluated on too few later tasks to provide reliable feedback for training it. Hence, we need sufficiently many tasks in each segment.

Third, the stream of tasks must create both an opportunity and a need to use memory. If the base model can already solve later tasks on its own, it has little incentive to rely on memory. Conversely, if it cannot solve any task in the stream, the writer has little successful experience from which to learn to write memory. We therefore <strong class="md-plain"><em>order training tasks from easy to medium to hard</em></strong>, allowing the model to acquire useful knowledge before tackling tasks that might benefit from useful memories. As we show in Q4, this *training* order produces the best results even when the *test* tasks are not ordered by difficulty, suggesting that it helps the model learn to write more useful memories.

---

## Experiments

:::callout_begin type="note" title=" ":::
<strong class="md-runin">Setup at a glance.</strong>

- <strong class="md-runin"><em>Symbolic Alchemy.</em></strong> The 10 tasks of a stream share a hidden chemistry; a useful memory records the rules the agent uncovers by experimenting. We report the oracle-normalized performance over 20 held-out chemistries and its improvement from the first to the second half of each stream.
- <strong class="md-runin"><em>Codebase Adaptation.</em></strong> A stream of 19 bug-fixing instances comes from two repositories excluded from training; a useful memory records how each repository is organized and tested and which mistakes to avoid. We report the cumulative reward over the stream and the cumulative gain, which is the cumulative reward minus that of a stateless run that solves every instance from scratch.
- <strong class="md-runin"><em>Longer streams.</em></strong>  Two held-out streams of 26 and 27 bug-fixing issues, from repositories unseen in training, are more than twice as long as any training stream. They test whether the trained writer extrapolates to streams longer than those it was trained on.
:::callout_end:::

:::fold_begin title="Symbolic Alchemy: environment and metrics":::

![](assets/figures/fig06_alchemy_chemistry.png "*Figure 6.* **An example chemistry in Symbolic Alchemy.** Each node is a stone, described by its shape, size and color, and labeled with its value. Each colored arrow is a potion, which changes one of these properties."){style=width:min(380px,100%)}

<strong class="md-runin">1)</strong> [**Symbolic Alchemy**](https://arxiv.org/abs/2102.02926)[**.**](https://arxiv.org/abs/2102.02926) *Symbolic Alchemy* is a toy environment in which the knowledge to be identified by solving a stream of tasks is the hidden set of rules that underlie the environment. In each task, the agent receives a fresh set of stones and potions. As shown in Figure 6, applying a potion to a stone changes the stone's properties (color, size or shape); placing a stone in the cauldron adds its value to the score. The goal of each task is to maximize this score, and the agent can see the current value of every stone but not the rules that change it. A hidden chemistry determines these transformations and values. The chemistry stays fixed across a stream of 10 tasks and is resampled between streams, so rules found in early tasks hold for the rest of the stream but do not carry over to other streams.

We evaluate on 20 held-out chemistries from the hardest level, in which the chemistry allows the fewest transitions between stone states, so high-value stones are the hardest to reach. Let $r_t$ be the agent's score on trial $t$ (the $t$-th task in the stream) and $r^{*}_t$ the score of an oracle that knows the chemistry. Performance is the mean normalized score across all 10 trials, and improvement is the mean over the last five trials minus the mean over the first five:

$\displaystyle \text{Performance} = \frac{1}{10}\sum _{t=1}^{10} \frac{r_t}{r_t^{\ast}}, \qquad \text{Improvement} = \frac{1}{5}\sum _{t=6}^{10} \frac{r_t}{r_t^{\ast}} - \frac{1}{5}\sum _{t=1}^{5} \frac{r_t}{r_t^{\ast}}$

:::fold_end:::

:::fold_begin title="Codebase Adaptation: test stream and metrics":::

![](assets/figures/fig07_clbench_protocol.png "*Figure 7.* **Evaluation protocol in** [**Continual Learning Bench**](https://arxiv.org/abs/2606.05661)**.** The same stream of instances is run twice, once by the continual learning system, which carries its state from one instance to the next, and once by a stateless baseline that is reset before every instance. The gain is the difference between the two cumulative rewards.")

<strong class="md-runin">2)</strong> [**Codebase Adaptation.**](https://github.com/pgasawa/continual-learning-bench/tree/main/src/tasks/codebase_adaptation) *Codebase Adaptation* is a task from [*Continual Learning Bench*](https://arxiv.org/abs/2606.05661), in which a model implements code while acquiring procedural knowledge about the codebase on the fly (e.g., how a repository is organized, which tests to run, which debugging steps pay off).  The test stream consists of 19 bug-fixing instances from two repositories excluded from training: 9 from tablib, followed by 10 from tenacity. The agent solves them sequentially, carrying a textual memory between instances.

We run each system five times, shuffling the order of the instances within each repository, while keeping the repository order fixed. In this case, useful knowledge includes code layout, test commands, and mistakes to avoid. Each instance is scored with a reward between 0 and 1. A patch that passes the hidden tests on the first turn earns 1, and the reward falls linearly with each additional turn. A patch that fails, or an attempt that runs out of its turn budget, earns 0. Let $\bar{r} _i$ be the reward on instance $i$, averaged over the five runs. The ***cumulative reward*** sums it over the 19 instances, so it reflects both how many instances are solved and how quickly:

$$
\displaystyle \text{Cumulative reward} = \sum _{i=1}^{19} \bar{r} _i
$$

To measure the benefit of prior experience, we also evaluate each system in a stateless configuration that resets its carried state before every instance, which in effect forces the model to solve each task from scratch. ***Cumulative gain*** is the score with carried memory or experience minus the stateless score, so it is positive when carrying experience helps and negative when it hurts. Both configurations use the same checkpoint, separating the benefit of prior experience from the model’s standalone bug-fixing ability. We use Qwen3.5-4B, with thinking enabled for both the actor and writer roles. We evaluate frontier models (Claude Opus 5.5, GPT-5.6 Sol, GPT-6 Astra) on the same task stream and also report leaderboard results for other frontier models and for coding agents (Claude Code, Codex). Each is compared with its own stateless run.

$$
\text{Cumulative gain} = \text{Cumulative reward} _{\text{memory}} - \text{Cumulative reward} _{\text{stateless}}
$$

<strong class="md-runin">Why these two domains.</strong> Symbolic Alchemy tests whether training can teach a model to capture a compact set of hidden rules in memory through experimentation. A codebase, by contrast, has no comparable set of hidden rules and is too large to memorize in full. A good memory instead captures procedures and warnings that make the next issue easier to fix, without attempting to describe the entire repository. These domains therefore test complementary challenges: in Symbolic Alchemy, the main bottleneck is discovering the right *latent* model of the world; in a codebase, it is turning observations into structured, actionable memory.

:::fold_end:::

:::fold_begin title="Training data":::

In Symbolic Alchemy, each training stream has its own hidden chemistry. Streams are harder when their chemistry graphs have fewer edges, since fewer transitions are available and high-value stones are harder to reach. We train on 950 streams, ordered from easy to hard and disjoint from the test streams.

For Codebase Adaptation, we use a dataset derived from SWE-smith, a training-scale SWE dataset created by injecting bugs into real Python repositories. We select 53 repositories excluded from the Codebase Adaptation evaluation and divide corruption strategies into three difficulty levels based on the untrained model’s success rate. Easy bugs involve local edits, such as a swapped operator or reordered statements; hard bugs require rebuilding larger pieces of logic, such as a removed loop or a rewritten function. Each injected bug, together with the tests that expose it, forms one task.

From these tasks, we construct training streams. Each stream is a sequence of 12 tasks made of two segments, where each segment contains six tasks from a single repository, ordered from easy to hard. Six tasks per segment allow knowledge to accumulate and provide opportunities to measure the effect of memory on later tasks. The early tasks are likely to be solved, so the agent learns how the repository is organized and how its tests are run, and the harder tasks that follow show whether the memory written from that experience helps. A shuffled order more often puts hard tasks first, which leaves the writer little useful experience to work with. The Codebase Adaptation streams are not ordered by difficulty, and the training data ablation below shows that training on ordered streams still yields better results on them than training on shuffled ones. The final set contains 382 streams and 4,584 tasks. No task appears in more than one stream, and no function is corrupted twice within a segment. Our training task sets are made public [here](https://huggingface.co/datasets/Racktic/memory-writing-train-tasks).

:::fold_end:::

:::fold_begin title="Held-out long streams":::

To test generalization to longer streams, we build two more streams from SWE-smith repositories used neither in training nor in Codebase Adaptation. One of them has two segments of 13 issues, and the other has three segments of 9 issues. Each stream thus has 26 or 27 issues, more than twice the length of a training stream and longer than the Codebase Adaptation stream. Evaluation follows the Codebase Adaptation protocol.

:::fold_end:::

### Main results on Codebase Adaptation

We compare our method on Codebase Adaptation with the base model, frontier models with in-context learning, coding agents, and recent methods for training memory writing. Our main findings are described below.

<table>
<thead>
<tr class="nbg-gray"><th><strong>System</strong></th><th><strong>Harness / Scaffold</strong></th><th><strong>Cumulative reward</strong></th><th><strong>Cumulative gain</strong></th></tr>
</thead>
<tbody>
<tr class="nbg-orange"><td>Gemini 3.1 Pro*</td><td>in-context learning</td><td>5.13</td><td>−1.55</td></tr>
<tr class="nbg-orange"><td>Gemini 3 Flash*</td><td>in-context learning</td><td>7.42</td><td>−0.33</td></tr>
<tr class="nbg-orange"><td>GPT-5.4*</td><td>in-context learning</td><td>10.14</td><td>+0.69</td></tr>
<tr class="nbg-orange"><td>Claude Opus 4.7*</td><td>in-context learning</td><td>10.36</td><td>+1.49</td></tr>
<tr><td>GPT-5.6 Sol</td><td>in-context learning</td><td>15.20</td><td>+4.71</td></tr>
<tr><td>Claude Opus 5.5</td><td>in-context learning</td><td>17.40</td><td>+0.90</td></tr>
<tr><td>GPT-6 Astra</td><td>in-context learning</td><td>17.25</td><td>+2.26</td></tr>
<tr class="nbg-yellow"><td>Claude Sonnet 4.6*</td><td>Claude Code</td><td>6.63</td><td>+0.73</td></tr>
<tr class="nbg-yellow"><td>GPT-5.4*</td><td>Codex</td><td>7.45</td><td>−0.80</td></tr>
<tr><td>Qwen3.5-4B</td><td>in-context learning</td><td>0.82</td><td>−0.02</td></tr>
<tr><td>Qwen3.5-4B, untrained</td><td>our ACT + WRITE loop</td><td>1.33</td><td>+0.48</td></tr>
<tr><td>Qwen3.5-4B, CoD</td><td>our ACT + WRITE loop</td><td>3.56</td><td>−0.16</td></tr>
<tr><td>Qwen3.5-4B, SkillRise</td><td>our ACT + WRITE loop</td><td>7.25</td><td>+0.60</td></tr>
<tr class="nbg-green"><td><strong>Qwen3.5-4B, Ours</strong></td><td>our ACT + WRITE loop</td><td><strong>10.55</strong></td><td><strong>+2.27</strong></td></tr>
</tbody>
</table>

::gray[*Table 1.* **Main results on Codebase Adaptation.** Each system's cumulative gain is measured against its own stateless run. While not an apples-to-apples comparison, observe that the cumulative gain from our approach is similar to that of GPT-6 Astra and far superior to any other method applied onto our base model, Qwen3.5-4B. (\* denotes results taken directly from the Continual Learning Bench ]::[::gray[leaderboard]::](https://continual-learning-bench.com/leaderboard.html)::gray[).]::

<strong class="md-plain">Training memory writing brings a 4B model to the level of frontier models.</strong> Our method raises the cumulative reward of Qwen3.5-4B from nearly zero to that of GPT-5.4 and Claude Opus 4.7 with in-context learning, and well above prior methods CoD and SkillRise trained in the same setting. While not directly comparable, our approach attains a cumulative gain from memory writing that roughly matches GPT-6 Astra and is only below GPT-5.6 Sol.

<strong class="md-plain">Solving more tasks is not the same as learning from earlier ones.</strong> Cumulative reward and cumulative gain rank the frontier models differently. Claude Opus 5.5 reaches the highest reward in the table but gains little from its history, while both Gemini models do worse with their history than without it. A model can be strong on the immediate task and still extract little from its past experience, which is why we report this gain metric alongside reward.

<strong class="md-plain">Wrapping frontier models in coding harnesses does not change the picture.</strong> Claude Code and Codex come with their own tools, context management plans, and persistent notes. Even so, Codex performs worse with its history than without it, and Claude Code gains little. Codex also falls below its own underlying model, GPT-5.4, with plain in-context learning, so the agent harness by itself does not turn past experience into better performance later.

<strong class="md-plain">Our acting/memory writing scaffold alone does not account for the improvement.</strong> The untrained Qwen3.5-4B gains nothing with in-context learning, and placing it in the ACT + WRITE loop helps only slightly. It writes a memory, but the memory hardly affects its performance on later instances. Training with our approach, rather than the scaffold itself, is therefore what enables the improvement.

### **Q1. Do we need to train for memory writing?**

We next ask whether prompting alone is sufficient for models to write useful memories or whether explicit training is needed.

<table>
<thead>
<tr class="nbg-gray"><th><strong>System</strong></th><th><strong>Writer</strong></th><th><strong>Performance</strong></th><th><strong>Improvement</strong></th></tr>
</thead>
<tbody>
<tr><td>Qwen3-4B</td><td>prompted</td><td>0.301</td><td>+0.086</td></tr>
<tr><td><strong>Qwen3-4B, ours: co-train</strong></td><td><strong>trained</strong></td><td><strong>0.490</strong></td><td><strong>+0.213</strong></td></tr>
</tbody>
</table>

::gray[*Table 2.* **Results on Symbolic Alchemy.** Both rows use the same model, with the writer either prompted or trained with our method.]::

<strong class="md-plain">Even though the “oracle” memory in the Alchemy environment simply needs to record the underlying rules, memory written via prompting fails to identify these.</strong> The environment in Alchemy is fully specified by a small set of rules, so the writer only has to extract those rules from a few tasks and pass them on to fully succeed on later tasks. Table 2 shows that when Qwen3-4B is only prompted to write a memory after each task, without any training, its later tasks improve only slightly on its earlier ones. Training the actor and the writer together changes the memory the model writes and, in turn, raises both performance and improvement substantially.

<strong class="md-plain">In Codebase Adaptation, training is necessary, but not every form of training works.</strong> Table 1 shows that, without training, the acting and writing loop barely helps Qwen3.5-4B on later tasks. The related CoD and [SkillRise](https://arxiv.org/abs/2607.26784) approaches, which train the model on the same streams using raw downstream rewards for the actor or writer, improve cumulative reward but achieve much smaller gains than our method. Turning experience into a better starting point for solving later tasks therefore depends on what the training objective is, and the next question studies this choice.

### **Q2. Which signal should train the writer?**

Having established that the writer must be trained, we ask how it should be trained. We vary the writer’s objective while holding actor training fixed, including its exploration reward.

![](assets/figures/fig08_writer_training.png "Figure 8. ***Effect of writer training on performance***, with the actor trained the same way in every case. Top: performance and cumulative reward. Bottom: improvement and cumulative gain.")

We compare trained and untrained writers on both domains. As shown in Figure 8, both the overall performance and the benefit from memory are substantially higher when the writer is trained, as discussed above in Q1. In some of our early experiments, we observed that untrained memories tended to violate formats, and we suspected that this led to poor downstream benefits from memory. To test this hypothesis, we also trained a memory writer with a generic format reward only, agnostic of the improvement that the underlying memory brings about. On Codebase Adaptation, adhering to a fixed memory format does slightly improve cumulative reward, but does not improve cumulative gain. Producing well-formed memory is therefore insufficient; the training signal must reflect its usefulness for later tasks, as ours does.

### **Q3. Does effective memory writing need the actor to explore? And how do exploration dynamics look through training?**

The writer learns from the actor’s experience. We therefore test how the actor’s exploration reward affects performance with trained and untrained writers. We show some examples at the end of this post.

![](assets/figures/fig09_exploration_reward_effect.png "*Figure 9.* **The effect of exploration reward, with a trained or untrained writer**. From left to right: performance and improvement in Symbolic Alchemy, cumulative reward and cumulative gain in Codebase Adaptation.")

<strong class="md-plain">Combining a trained writer with an actor rewarded for exploration yields the best performance of the four configurations (Figure 9).</strong> In Symbolic Alchemy, using an exploration reward barely changes performance with an untrained writer, but is essential for writer training to help: without it, the trained writer performs worse than the untrained one. In Codebase Adaptation, exploration improves both cumulative reward and cumulative gain regardless of whether the writer is trained, roughly doubling cumulative gain even with an untrained writer. With a trained writer, removing exploration makes cumulative gain negative, pushing performance below the model’s own stateless baseline. Together, these results suggest that effective memory writing depends on collecting exploratory experience that transfers beyond the current task; without it, the writer has little useful new knowledge to preserve.

![](assets/figures/fig10_exploration_scores.png "*Figure 10.* **Exploration scores during training**, with (red) and without (blue) the exploration reward, and with a trained (solid) or untrained (dashed) writer.")

<strong class="md-plain">Our method sustains exploration while learning to write more useful memories.</strong> We next visualize how the exploration score evolves over the course of training on the training task streams. As shown in Figure 10, the exploration score remains roughly constant throughout training, which may seem surprising given that we explicitly optimize it. However, joint training creates two opposing effects. As the writer improves during training, it becomes harder for the actor to find useful information beyond what the memory already contains. The exploration reward encourages the actor to keep seeking such information. A stable score is therefore consistent with the actor keeping pace with an improving writer.

Without rewarding the actor for exploration, the score generally declines in Figure 10, suggesting that the actor does not sustain this information gathering on its own. With exploration rewarded but the writer untrained, scores instead rise above ours, yet cumulative reward and cumulative gain remain lower than those of our method. One explanation is the summarization problem described in the method section. An untrained writer tends to summarize or compress information with a bias toward the latest rollout, potentially overwriting information already present in memory. As a result, almost anything somewhat different the actor encounters on a given task can appear new, whether or not it helps future tasks. Our method’s stable exploration score, together with its stronger performance, suggests a productive balance between discovering new information and learning to preserve it for future tasks.

### **Q4. Does the construction of the training task streams matter?**

| **Training data form** | **Scaffold** | **Cumulative reward** | **Cumulative gain** |
| --- | --- | --- | --- |
| Single task | in-context learning | 2.93 | −0.29 |
| Single task | ACT + WRITE loop | 3.35 | −0.09 |
| Streams, 3 + 3, curriculum order | ACT + WRITE loop | 3.26 | +0.58 |
| Streams, 6 + 6, shuffled order | ACT + WRITE loop | 8.05 | +0.69 |
| **Streams, 6 + 6, curriculum order (ours)** | ACT + WRITE loop | **10.55** | **+2.27** |

::gray[*Table 3.* **Results on Codebase Adaptation for models trained on different data**. All models are evaluated on the same Codebase Adaptation test task stream from Continual Learning Bench, regardless of where the training data was constructed.]::

![](assets/figures/fig11_q4_pareto.gif "*Figure 11.* **Training data ablation on Codebase Adaptation.** Each point is a model trained on different data and evaluated on the same Codebase Adaptation tasks. Training on 6 + 6 curriculum streams (ours) achieves the highest cumulative reward and cumulative gain, and the shaded region marks the configurations it dominates.")

Our method trains on deliberately built task streams, and this section studies whether the construction of task streams in the training data matters. Recall that each training stream presents two repository segments of six tasks, with the tasks inside a segment ordered from easy to hard. We vary the construction in three steps: whether to train on streams at all, how to order the tasks within a segment, and how long a segment should be. Results are shown in Table 3 and Figure 11.

![](assets/figures/fig12_streams_vs_single_tasks.png "*Figure 12.* **Training on streams versus single tasks**, by position in the repository segment. Left: fraction of samples that pass. Middle: fraction of GRPO groups that produce a gradient. Right: outcomes of the groups at the two hardest positions.")

<strong class="md-plain">Training on single tasks teaches the model to solve tasks but not to carry experience by writing effective memories.</strong> Observe in Table 3 that training with GRPO on a single task at a time improves reward above that of the untrained model but keeps its cumulative gain near zero. In other words, the model learns to solve each task on its own and learns nothing about using one task to help with the next. Using task streams also changes what the training signal looks like on hard tasks, as Figure 12 shows. A model does not attain any reward on a task it cannot solve from scratch, and hence, sees no learning signal, when that task is trained on by itself. Within a stream of tasks, the memory from earlier tasks can bring a hard task within reach, so the same task starts to produce a learning signal.

<strong class="md-plain">Within a training stream, task order and segment length matter (Table 3).</strong> Shuffling the tasks within each segment, while keeping the repositories and task sets unchanged, lowers cumulative reward and substantially reduces cumulative gain. The easy-to-hard order thus helps make memories written on early tasks useful for later ones. Shortening segments from six tasks to three, while preserving the curriculum order, has an even larger effect. With only three tasks per repository, memory has fewer opportunities to accumulate useful knowledge and improve later performance, weakening the actor’s incentive to use it effectively. Because the actor can simply optimize task progress unless the memory is useful, whenever we are unable to learn to write effective memories, actor training will further inhibit the actor from productively using memories. The resulting model performs close to the single-task baseline. The writer learns what experience is worth retaining when later tasks provide opportunities to use it, and training task streams must therefore give that experience enough relevant tasks to demonstrate its value.

| **Training data** | **Cumulative reward (13 + 13)** | **Cumulative gain (13 + 13)** | **Cumulative reward (9 + 9 + 9)** | **Cumulative gain (9 + 9 + 9)** |
| --- | --- | --- | --- | --- |
| Streams, 3 + 3, curriculum order | 7.29 | −0.47 | 3.68 | −0.94 |
| Streams, 6 + 6, shuffled order | 9.88 | −0.36 | 9.29 | +0.98 |
| **Streams, 6 + 6, curriculum order (ours)** | **13.50** | **+0.81** | **12.35** | **+1.64** |

::gray[*Table 4.* **Results on the held-out long streams for the same models**. All models use the ACT + WRITE loop as their scaffold<em>.</em> Observe that training on longer streams (6 + 6) with an easy-to-hard curriculum ordering over tasks attains the highest cumulative reward and gain on extrapolated scenarios.]::

![](assets/figures/fig13_heldout_cumulative_gain.png "*Figure 13.* **Cumulative gain at each issue position on the held-out long streams**, averaged over the two streams. Our training streams end at issue 12. Shaded regions show ±1 standard error over runs with memory.")

<strong class="md-runin">Extrapolation results.</strong> Finally, we evaluate if our procedure allows us to extrapolate to longer sequences of tasks. As shown in Table 4, our approach still performs the best on streams more than twice as long as those used in training<strong>.</strong> Concretely, the two held-out streams contain 26 and 27 issues, compared with only 12 tasks in our training streams. Our model achieves the highest cumulative reward and cumulative gain on both. As shown in Figure 13, the cumulative gain of our method continues to rise beyond the twelfth issue (the length of our training streams), and continues to increase thereafter. In contrast, the cumulative gain of the model trained on shuffled segments soon levels off, while that of the model trained on three-issue segments declines over the later issues and ends below zero. These results suggest that giving memories repeated opportunities to be used during training helps the writer generalize to much longer streams, the extrapolation our training data was designed to support.

### **Q5. One policy or two?**

So far we have trained a single model to operate in both the actor and writer roles. Does parameter sharing help or hurt? To answer this question, we run a series of experiments where each role is provided its own separate set of parameters starting from a strong checkpoint obtained with our method. We call this checkpoint a “branch point”.

| **Variant** | **ACT** | **WRITE** | **Cumulative reward** | **Cumulative gain** |
| --- | --- | --- | --- | --- |
| co-train at the branch point | shared, trained | shared, trained | 8.84 | +0.72 |
| frozen writer | separate, trained from the branch point | frozen at the branch point | 8.80 | +0.02 |
| decoupled | separate, trained from the branch point | separate, trained from the branch point | 10.07 | +1.07 |
| **co-train (ours)** | **shared, continued from the branch point** | **shared, continued from the branch point** | **10.55** | **+2.27** |

::gray[*Table 5.* **Shared versus separate parameters for the actor and the writer on Codebase Adaptation**. All variants start from the same checkpoint of our method, the branch point, and are trained with identical rewards and data for the same number of steps. Continuing to train the shared policy (bold) gives the highest cumulative reward and cumulative gain.]::

<strong class="md-runin">Setup.</strong> We branch from a checkpoint of our method taken around iteration 300, at which point the co-trained model already performs both acting and memory writing well, and continue training under three regimes with identical rewards and data. We compare continued training of this co-trained policy with two variants initialized from the same checkpoint, in which the actor and the writer maintain a separate copy of the parameters and the writer is either frozen or trained. Results are shown in Table 5.

<strong class="md-plain">With a frozen writer, the actor’s gains from memory disappear.</strong> Freezing the writer and training the actor alone leaves cumulative reward roughly unchanged, while cumulative gain falls to nearly zero, below its value at the branch point. Note that in this experiment, during training and evaluation, the actor receives memories produced by the same fixed writer. This result highlights the need to train the actor and writer together: with a fixed writer, the actor can learn to increase exploration reward while relying less on memory for subsequent tasks.

<strong class="md-plain">Training the writer separately (“decoupled”) restores the gains, but sharing parameters is better.</strong> With a separately trained writer, both cumulative reward and gain improve over the starting point, but remain below those of the shared policy trained for additional steps. With shared parameters, the actor’s exploration reward and the writer’s improvement reward update the same weights, allowing learning in one role to benefit the other. Knowledge acquired through training the actor can therefore also inform memory writing. With separate policies, updates remain specific to each role, and the two policies must coordinate through the trajectories and memories they exchange. These results suggest that parameter sharing is not only cheaper, but also helps regularize training for the actor and writer.

## **Case studies: what does the trained writer write?\[under construction\]**

<strong class="md-plain">A memory that summarizes the last task does not help with the next one.</strong> In the example below, the untrained writer replaces its memory after each task with a summary of that task, while the trained writer keeps and extends a description of the repository. Only the actor given the trained writer’s memory solves the next task.

<iframe src="case-studies/case1_summarization.html" data-autoheight loading="lazy" style="width:100%;height:720px;border:1px solid #e5e5e5;border-radius:6px"></iframe>

[Open this case study in a new tab](case-studies/case1_summarization.html)

<strong class="md-plain">Without the improvement reward, the writer passes on memory that later tasks cannot rely on, even when that memory is well formed.</strong> In the examples below, a writer that receives no reward passes on a single test command, and a writer trained only for format leaves out how to submit, so the next actor fixes the bug but never submits the fix.

<iframe src="case-studies/case2_format.html" data-autoheight loading="lazy" style="width:100%;height:720px;border:1px solid #e5e5e5;border-radius:6px"></iframe>

[Open this case study in a new tab](case-studies/case2_format.html)

<strong class="md-plain">The trained writer keeps what the actor’s experience reveals about the environment, revises or generalizes it, and later tasks start from it.</strong> Each tab below follows one memory from the task where it is written to the task that revises or uses it.

<iframe src="case-studies/case3_cotrain.html" data-autoheight loading="lazy" style="width:100%;height:720px;border:1px solid #e5e5e5;border-radius:6px"></iframe>

[Open this case study in a new tab](case-studies/case3_cotrain.html)

<strong class="md-plain">The exploration reward scores what an update adds to the memory, not how much of its text changes.</strong> In one training stream, an update that records a new fix and a general rule receives 0.875, while one that rewrites every bullet of the previous memory in new words and adds a single detail receives 0.25.

<iframe src="case-studies/case_exploration.html" data-autoheight loading="lazy" style="width:100%;height:720px;border:1px solid #e5e5e5;border-radius:6px"></iframe>

[Open this case study in a new tab](case-studies/case_exploration.html)
