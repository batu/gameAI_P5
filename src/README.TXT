Spencer Smoot sssmoot
Enrique Molina enmolina
Batu Aytemiz baytemiz

There is a lot of unused code in our submission. For reading convenience
the sections are seperated by comment blocks. We are actively using the Vanilla
Search component, whereas BiDirectional Search, Relaxed Search Heuristic and
Learning Algorithm were all tried but in the end were decided not to be utilized.
We are keeping them in to show the attempted paths.

Heuristics:
We found several small heurisitcs that give incremental gains but when combined
allow us a pretty fast algorithm. The current submission results are not admissible
and sometimes finds non optimal paths. We believe we know where the pain points lie,
however the performance benefit seemed more useful then slight deviation in optimality.

Heuristic 1:
It invalidates the usage of lower technology items if you have a higher tech one.
Eg: Dont punch trees if you have an axe lying around

Heuristic 2:
If you already created enough of an item dont create more of it.
Eg: If you need 5 carts and 20 rails, dont create the 6th cart.

Heuristic 3*:
If you are producing something in the goal state thats good!
You can let go of states that dont have the goal state.
THIS HEURISITC DOES NOT HAVE ADMISIBILTY GUARANTEE!

Heuristic 4:
If you already have an REQUIRED item, dont create more of it.

Heuristic 5:
Every item is at max needed a certain amount. For example no recipe requires 2 wood to be created.
This means if you have that max amount, stop making more.
Never have more than 1 wood etc..

Cobble Heuristic:
Cobble is a specific case, at some point you never need to produce more cobble,
This heuristic allows this constraint.
(This could be an a specific version of heuristic 5, and could be generalized and be made dynamic.

Heuristic 6:
Two items, rails and carts are leaf items. They dont lead to anywhere
Which means those are not in the goals list, there is no reason to create them.
(This could be generalized and be made dynamic.)

Heuristic 7*: (line 756)
If a state is already seen, dont go there.
This helps with punch, craft vs craft, punch scenarios.
Important to note that this also introduces an inadmissiable heuristic to the system
as the active implementation doesnt take into consideration the cost.
When we make it so it takes (cost to get to the state, state) into consideration the performance hit was too big to
take and we tried to overcome this in different ways, it seems to not have worked.
The part after continiue is the implementation where it is admissible (albeit very slow)

We believe when heuristic 7 and 3 is disabled we have admisibility however the overall
algorithm takes a huge performance hit and overall we believe the current submission
is a better demonstration of our work.

# The paths we tried that didnt work

Rougly speaking in bi directional search and Learning algorithm the non treelike structure made it difficult for it to converge.
Learning didnt account for optimal paths (due to optimal paths changing when the amount
changes aka, making 1 bench is different than making 1000 because of the existance of
axes) Bi Directional had trouble keeping track of the moving frontier and having
the necesary heuristics to guide it properly to the target.

The backwards search would reach an initial state without hitting the forward search more often than not.
Both of these can be solved but due to time constraints we couldnt get it to work
reliably.

The plus of the relaxed search heuristic was not enough to offset its cost.


