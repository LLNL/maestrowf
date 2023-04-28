## Maestro's Foundation and Core Concepts
----

Maestro pulls its core concepts for executing computational workflows in an analogous fashion to what an experimentalist performs at a laboratory bench. [High performance computational resources](https://en.wikipedia.org/wiki/Supercomputer) are primarily focused on *studying* natural phenomena via [simulation (mathematical modeling)](https://en.wikipedia.org/wiki/Computer_simulation), and therefore follow a similar thought pattern. At the highest level, an experimentalist is responsible for the following:

1. Establishing, documenting, and communicating processes for running experiments
2. Running experiments over multiple parameters consistently
3. Repeating experiments on new and existing parameters

<br/>
### Maestro Studies

We have designed Maestro around the core concept of what we call a "study". A study is defined as a set of steps that are executed (a workflow) over a set of parameters. A study in Maestro's context is analogous to an actual tangible scientific experiment, which has a set of clearly defined and repeatable steps which are repeated over multiple specimen.

Maestro is designed around the principles of self-documentation, consistency, and repeatability.

![Reproducibility, the intersections of documentation, consistency, & repeatability](../assets/images/reproducibility_venn.svg){: height="45%" width="45%" align=left}
#### Repeatability

Studies should be easily repeatable. Like any well-planned and implemented science experiment, a process should be run exact;y the same way each time for each parameter or over different runs of the study itself.

#### Consistent

Studies should be run in a consistent fashion. The removal of variation in the process means less mistakes when executing studies, ease of sharing with others, and uniformity in defining new studies.

#### Self-documenting

Documentation is critical in studies. The Maestro YAML Specification is an artifact documenting a complete workflow.

## Reproducible Science
----


``` mermaid
flowchart TB
    subgraph Initial [ ]
      direction LR
      subgraph Process [ ]
        direction LR
        A(Scientist #1)-->B(Experimental Process)
      end
    B-->E
    B-->G
    B-->I
    subgraph Laboratory
      direction TB
        subgraph Exp1 [Experiment 1]
          direction LR
          E(Parameter Set 1) --> F(Process)
        end
        subgraph Exp2 [Experiment 2]
          direction LR
          G(Parameter Set 2) --> H(Process)
        end
        subgraph Exp3 [Experiment 3]
          direction LR
          I(Parameter Set 3) --> J(Process)
        end
    end
    subgraph Data
      direction TB
      F-->K(Dataset 1)
      H-->L(Dataset 2)
      J-->M(Dataset 3)
    end
    K-->N(Analytics)
    L-->N
    M-->N
    end
      Initial--Share Process-->Peers
      subgraph Peers
          direction TB
          C(Scientist #2)
          D(Scientist #3)
      end
```

Maestro aims to replicate the physical sciences' experimental processes in the computational domain

``` mermaid
flowchart TB
    subgraph Initial [ ]
      direction LR
      subgraph Process [ ]
        direction LR
        A(User #1)-->B(Computational Process)
      end
    B-->E
    B-->G
    B-->I
    subgraph HPC
      direction TB
        subgraph Exp1 [Computational Experiment 1]
          direction LR
          E(Parameter Set 1) --> F(Process)
        end
        subgraph Exp2 [Computational Experiment 2]
          direction LR
          G(Parameter Set 2) --> H(Process)
        end
        subgraph Exp3 [Computational Experiment 3]
          direction LR
          I(Parameter Set 3) --> J(Process)
        end
    end
    subgraph Data
      direction TB
      F-->K(Dataset 1)
      H-->L(Dataset 2)
      J-->M(Dataset 3)
    end
    K-->N(Analytics)
    L-->N
    M-->N
    end
      Initial--Share Process-->Peers
      subgraph Peers
          direction TB
          C(User #2)
          D(User #3)
      end
```

The fundamental unit of work in Maestro is the yaml based [study specification](../Maestro/specification.md).  This specification not only gets used in executing/performing and documenting experiments using a set process: it also facilitates the sharing of that process to other users, enabling them to repeat/reproduce those experiments.
