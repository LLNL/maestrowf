As we mentioned on the [Background](./index.md) page, the general definition of
a **workflow** is a process of tasks that may be dependent on one another. Let's revisit
the bread recipe:

???+ example "Baking Bread"
    The high level set of tasks for baking bread are:

    1. Mix flour and water
    2. Mix in the yeast
    3. Fold the dough
    4. Proof the dough


Now, you must be wondering why we keep going back to this bread recipe. Simply put,
it is something most people understand without getting lost in detail (which we will
revisit later). Again, for now, let's ignore implementation; instead, let's just simply
focus on the tasks to make bread. The steps are numbered in order of execution,
meaning that you can not mix in the yeast until you've created the dough by mixing
the flour and water. By extension, you cannot proof the dough until you fold the
dough, but you must also mix the flour and and water. This recipe forms a linear
dependency.

In Computer Science, we can map the idea of a recipe to an abstract data structure
known as a graph. A graph is capable of capturing not only data, but also dependencies
between different data entries.

<br/>

## What are Graphs?
----

A [graph](https://en.wikipedia.org/wiki/Graph_(discrete_mathematics)#Graph) at its core
is a discrete mathematics concept that defines a structure and is defined by both a set
of vertices and a set of edges. Vertices describe nodes in a graph, whereas edges
describe the connections between them. In terms of representing a [workflow](./index.md#what-are-workflows?), we're primarily interested in a
[directed graph](https://en.wikipedia.org/wiki/Directed_graph)
because edges can be traversed in only one direction. This limitation is useful as
it enforces forward movement in processes. Let's revisit the bread recipe above,
except this time looking at it from the perspective of a graph.

???+ example "A Bread Recipe Graph"

    We previously established that the bread recipe steps are a linearization, or a
    linear chain of steps. We must complete the steps in sequential order in order
    to make bread. Here's how that looks as a graph:

    ``` mermaid
    graph TD;
        A(Mix flour + water)-->B(Mix in Yeast);
        B-->C(Fold dough);
        C-->D(Proof dough);
    ```

    If we want to extend the graph to include the baking of the bread, this means
    we must complete all the previous steps and then bake our prepared loaf. That
    simply is represented as a new edge from `Proof dough` to a new node called
    `Bake loaf` and would look as follows:

    ``` mermaid
    graph TD;
        A(Mix flour + water)-->B(Mix in Yeast);
        B-->C(Fold dough);
        C-->D(Proof dough);
        D-->E(Bake loaf);
    ```

Now, you'll notice that the edges in the example above have arrows; these arrows
represent the direction that these edges must be traversed. This property means
that, when scanning through a graph, the ordering of events is preserved. For
example, in the recipe graph above, you can not attempt to bake a loaf of bread
before mixing the flour and the water because there are no edges pointing in that
direction.

## How does a Bread Recipe Help You?

So you might be wondering, how does a bread recipe help me? I develop software,
run things on super computers -- what use is a graph about bread? Let's revisit
the definition of workflow and **intent**. Let's use a typical workflow seen in
high-performance computing as an example; simulation.

???+ example "A Typical Simulation Workflow"

    The primary focus of high-performacne computing is to model physical phenomena
    and learn about them by constructing scenarios that represent controlled
    experiements. This paradigm often boils down to a workflow characterized
    by the following high-level process:

    1. Setup system inputs
    2. Simulate the system
    3. Post-process the results

    Most simulation codes require some input files (parameter values, meshes,
    force fields) to run models of a system, meaning that there is a dependence
    between simulation and input setup. Further, you can not post process results
    you do not have; therefore post processing is dependent on simulation. If a
    step in this chain fails, it blocks the rest from being completed. This process
    is a linearization just like the process of baking bread.

	``` mermaid
    graph TD;
        A(Setup inputs)-->B(Simulate);
        B-->C(Post Process);
	```

!!! try-it "Try it: Breakdown You Own Workflow into a Process"
    **Exercise:** Take a moment and think about one of your own workflows. It can be something in your daily routine or a technical item that requires multiple steps to complete (commands, or scripts, etc.). In much the same way that the recipe above is an abstract set of steps without implementation, try to break down your own workflow into an intent-based process. Some questions to think about as you come up with a process:

    - What are the natural divisions of work that appear?
    - Are there places where the process is unclear?
    - Could you describe your process to another person without describing implementation?
    - Is it easier to describe the goal of the work without resorting to implementation for detail?

    **Goal:** The goal of this exercise is to start thinking with an intent-based mindset. While implementation is useful, explaining a workflow to others (especially those in other domains) by implementation is confusing and difficult. Boiling a process up to intent provides a conceptual substrate that allows others to more easily follow why a workflow is needed and then understand why each step in he process is needed.

    **Extra Credit:** Describe your workflow to someone else. If the workflow was unclear, was the other person able to effectively ask questions or discuss with you?
