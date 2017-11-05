import json
from collections import namedtuple, defaultdict, OrderedDict
from timeit import default_timer as time
from _heapq import heappop, heappush
from math import inf

Recipe = namedtuple('Recipe', ['name', 'check', 'effect', 'relaxed_effect', 'cost'])



#A wrapper functino over effectors in the CookBookEntry representation
#Helps with keeping track of what effector is linked to what and creates what etc.
class EffectorWrapper():
    def __init__(self, effector, creates, cost, recipe_name):
        self.effector = effector
        self.creates = creates
        self.recipe_name = recipe_name
        #There are some items that are catalysts that you only need one.
        self.required = False
        self.cost = cost
        self.creates_dict = 0

    def __call__(self, *args, **kwargs):
        return self.effector(args[0])

    def __str__(self):
        return str("This is a {} effector.".format(self.creates))

# Node representation for A* to help readability
class Node():
    def __init__(self, name, state, cost, effect = None):
        self.name = name
        self.state = state
        self.cost = cost
        self.effect = effect
        self.total_cost = 0

    def __lt__(self, other):
        return self.cost < other.cost

    def __str__(self):
        return "ChildNode name:{} and state{}".format(self.name, self.state)

# A datastructure that keeps hold of lots of information regarding cookbook entries
class CookBookEntry():

    def __init__(self, recipe_name, cost, effector, requires = None, consumes = None, produces = None):
        self.name = recipe_name
        self.requires = requires
        self.consumes = consumes
        self.produces = produces
        self.cost = cost
        self.effector = effector

        #What the action is called vs what it produces are two seperate things
        self.ProductName = None

        # Most importantly the path of effectors that is needed from {} to {name}
        self.path = []
        self.actively_learned = False
        self.catalyst = None

    #Hash on the name
    def __hash__(self):
        return hash(self.name)

    def __str__(self):
        return str("Name:{}\nRequres:{}\nConsumes:{}\nProduces:{}\nCost:{}\nEffector:{}\nProductName:{}\nPath:{}\n".format(\
            self.name, self.requires, self.consumes, self.produces, self.cost, self.effector, self.ProductName, self.path))

    #Updates the product name based on what is produced.
    def updateProductName(self):
        self.ProductName = list(self.produces.keys())[0]
        self.effector.creates = self.ProductName
        self.effector.creates_dict = self.produces

    #Updates the path by taking in the path that is necesary to get to state where
    # you can add its own effector and get to the result
    def updatePath(self, path_needed_to_get_here):
        if path_needed_to_get_here:
            self.path += path_needed_to_get_here
        self.path.append(self.effector)

class State(OrderedDict):
    """ This class is a thin wrapper around an OrderedDict, which is simply a dictionary which keeps the order in
        which elements are added (for consistent key-value pair comparisons). Here, we have provided functionality
        for hashing, should you need to use a state as a key in another dictionary, e.g. distance[state] = 5. By
        default, dictionaries are not hashable. Additionally, when the state is converted to a string, it removes
        all items with quantity 0.

        Use of this state representation is optional, should you prefer another.
    """

    def __key(self):
        return tuple(self.items())

    def __hash__(self):
        return hash(self.__key())

    def __lt__(self, other):
        return self.__key() < other.__key()

    def copy(self):
        new_state = State()
        new_state.update(self)
        return new_state

    def __str__(self):
        return str(dict(item for item in self.items() if item[1] > 0))

#path is a list of effect functions,
#Creates the item from a given path
# Final implementatino doesnt use this.

#############################################################################
################ PATH LEARNING RELATED FUNCTIONS ############################
#vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv#

#updates the entry to show whether it is a catalyst (only one is needed)
#Iterates through the whole cookbook and updates the necesary components
def updateRequired(cook_book):
    for entry in cook_book:
        if entry.requires:
            requirements = entry.requires.keys()
            for requirement_key in requirements:
                required_cook_book_entry = next((e for e in cook_book if e.ProductName == requirement_key), None)
                if required_cook_book_entry.catalyst: continue
                required_cook_book_entry.catalyst = True
                required_cook_book_entry.effector.required = True
                REQUIRED_ITEMS.add(required_cook_book_entry.ProductName)
                #print("Updated catalyst for {}".format(required_cook_book_entry.name))

#Decides whether a cook book entry is primitive, aka, doesnt require or consume anything.
def isPrimitive(cook_book_entry):
    if cook_book_entry.requires == None and cook_book_entry.consumes == None:
        print("{} is a primitive!".format(cook_book_entry.name))
        return True
    return False

#Takes a path and gets the goal state by using the steps in the path.
#Makes sure all the goals are satisfied
def use_paths_get_goal(cook_book, state, goal):
    current_state = state

    while not (is_goal(current_state)):
        for key in goal.keys():
            if current_state[key] < goal[key]:
                cook_book_entry = next((entry for entry in cook_book if entry.ProductName == key), None)
                print("Making {} from current state:{}".format(cook_book_entry.name, current_state))
                current_state = walk_path(current_state, cook_book_entry.path, goal)
    return current_state

# A single strand version of use_paths_get_goal.
# Simply iterates through the path of effectors ensuring stupid things are not done.
# Aka make more than needed catalyst etc...
def walk_path(state, path, goal):
    current_state = state
    for effect in path:
        if effect.required and  state[effect.creates] >= 1 and effect.creates not in goal.keys():
            continue
        current_state = effect(current_state)
        print(current_state)
    return current_state

# Creates a cook book entry.
def create_cookbook_entry(recipe_name, recipe, rule):
    newCookBookEntry = CookBookEntry(recipe_name, recipe.cost, EffectorWrapper(recipe.effect, recipe_name, recipe.cost, recipe_name))
    #newCookBookEntry = CookBookEntry(name, recipe.cost, recipe.effect)

    if "Requires" in rule.keys():
        newCookBookEntry.requires = rule["Requires"]
        requires = True

    if "Consumes" in rule.keys():
        newCookBookEntry.consumes = rule["Consumes"]
        consumes = True

    if "Produces" in rule.keys():
        newCookBookEntry.produces = rule["Produces"]
        produces = True
        #print("In {} updated produces ={}".format(name, rule["Produces"]))


    newCookBookEntry.updateProductName()
    #print("In the creation")
    #print(newCookBookEntry)
    return newCookBookEntry

# The main engine. This basically learns all the shortests paths to all necesary
# goals and updates the paths of those items as required.
def learn_shortest_paths(cook_book, goal):
    # if goal is already known, return its path, and own effector added to it
    # else check the components needed to make it and learn them
    active_goals = list(goal.keys())

    # Recursively learns.
    # Takes a goal
    # Learn(goal)
    # Asks if I know how to build that goal (check if that entry attached with that goal has a path)
    # If yes, return the path
    # If no, look at what is necesary to build the object.
    # Learn(sub_parts)
    # repeat until you find a primitive action you already know.
    # Now you know how to make the sub parts.
    # If you know how to make the sub parts, you know how to make yourself by adding
    #your own active effector to the list of paths that is contained in the subparts
    # No you know how to get to the goal

    # Unfortunately currently bugged as it doesnt take into consideration the time factor.
    # I feel my work on this spread too far away from the spirit of the assignment so I stopped.
    def learn(goal):
        goal_entry = next((entry for entry in cook_book if entry.ProductName == goal ), None)
        while not goal_entry.path:
            for cook_book_entry in cook_book:
                if goal == cook_book_entry.ProductName:
                    if cook_book_entry.path:
                       return cook_book_entry.path
                    else:
                        needed_list = []
                        if cook_book_entry.requires:
                            needed_list += list(cook_book_entry.requires.keys())
                        if cook_book_entry.consumes:
                            needed_list += list(cook_book_entry.consumes.keys())
                        learning_path = []
                        #print("Needed list in shortest_path:{}".format(needed_list))
                        #print("Learning path in shortest_path:{}".format(learning_path))
                        for needed in needed_list:
                            needed_entry = next((entry for entry in cook_book if entry.ProductName == needed ), None)
                            # If you already started learning the goal you dont need to start again.
                            if not needed_entry.actively_learned:
                                needed_entry.actively_learned = True
                                learning_path += learn(needed)
                            else:
                                continue
                        cook_book_entry.updatePath(learning_path)
                        return cook_book_entry.path
        return goal_entry.path

    #Learn each goal.
    for goal in active_goals:
        learn(goal)
    print("Learning complete.\n")
    return

def composite_goal(cook_book, goals):
    learn_list = []
    for goal_key in goals.keys():
        for entry in cook_book:
            if entry.ProductName == goal_key:
                learn_list.append()
                return

def learn_from_search(cook_book, goal):
    return
#^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^#
################# END OF LEARNING RELATED FUNCTIONS #######################
#############################################################################


#############################################################################
############ BI DIRECTIONAL A* RELATED FUNCTIONS ############################
#vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv#

def backwards_graph(state, all_states):
    # Iterates through all recipes/rules, checking which are valid in the given state.
    # If a rule is valid, it returns the rule's name, the resulting state after application

    # to the given state, and the cost for the rule.
    all_nodes = []
    for r in all_backwards_recipes:
        if r.check(state):
            # This ensure we dont go through duplicate paths.

            new_state = r.effect(state)

            if (new_state, new_state.total_time_cost) in all_states:
                continue
            all_states.add(new_state, new_state.total_time_cost)

            effector_wrapper = EffectorWrapper(r.effect, r.name, r.cost, r.name)
            all_nodes.append(Node(r.name, new_state, r.cost, effector_wrapper))
    return all_nodes

def make_backwards_checker(rule):
    # Implement a function that returns a function to determine whether a state meets a
    # rule's requirements. This code runs once, when the rules are constructed before
    # the search is attempted.

    #print("Printing rule: {}".format(rule))
    #{'Produces': {'stone_axe': 1}, 'Requires': {'bench': True}, 'Consumes': {'cobble': 3, 'stick': 2}, 'Time': 1}
    #The checker’s role is to assess whether a crafting recipe is valid in a given state.
    #State is the stuff you have.

    #{'bench': True}
    #{'plank': 3, 'stick': 2}
    def backwards_check(state):
        # This code is called by graph(state) and runs millions of times.
        # Tip: Do something with rule['Consumes'] and rule['Requires'].

        requires = None
        produces = None
        if "Requires" in rule:
            requires = rule["Requires"]
        if "Produces" in rule:
            produces = rule["Produces"]


        #if it consumes any items
        if produces:
            for produced, amount in produces.items():
                if produced not in state:
                    return False
                if not (amount <= state[produced]):
                    return False
        # same as above

        if requires:
            for required in requires:
                if not required in state:
                    return False
                if state[required] < 1:
                    return False


        #Reaching here means we have all of what we need
        return True

    return backwards_check

def make_backwards_effector(rule):
    # Implement a function that returns a function which transitions from state to
    # new_state given the rule. This code runs once, when the rules are constructed
    # before the search is attempted.

    #The effector’s function is
    #to return the state resulting from applying the rule to a given state.
    def backwards_effect(state):
        # This code is called by graph(state) and runs millions of times
        # Tip: Do something with rule['Produces'] and rule['Consumes'].

        #Copy the state.
        next_state = state.copy()
        consumes_list = None
        produces_list = None
        require_list = None
        if "Consumes" in rule:
            consumes_list = rule["Consumes"].items()
        if "Produces" in rule:
            produces_list = rule["Produces"].items()

        if "Requires" in rule:
            require_list = rule["Requires"].items()

        #Update the sate by consuming the amount of items
        if consumes_list:
            for consumed, amount in consumes_list:
                if consumed in next_state.keys():
                    next_state[consumed] += amount
                else:
                    next_state[consumed] = amount

        if require_list:
            for reqired in require_list:
                next_state[reqired] = 1

        #add the amount of items produced to state.
        if produces_list:
            for produced, amount in produces_list:
                next_state[produced] -= amount

        return next_state
    return backwards_effect

def reached_ground_zero(state):
    s = {key: value for key, value in state.items()
             if value != 0}

    if s == {}:
        return True

def bi_goal(state_1, state_2):
    s_1 = {key: value for key, value in state_1.items()
             if value != 0}
    s_2 = {key: value for key, value in state_2.items()
             if value != 0}

    if s_1 == s_2:
        return True
    return False
"""
    for item, amount in s_1.items():
            #print("Printing item:{}".format(item))
            #print("Printing amount :{}".format(amount))
        if item not in s_2.keys():
            return False
        elif amount > s_2[item]:
            return False
"""

def bi_search(graph, state, is_goal, limit, heuristic, goal):

        if is_goal(state):
            return []

        start_time = time()
        queue = []
        closed_set = []

        current_state = state
        current_node = Node("Initial inventory.", current_state, 0)

        current_backwards_state = State({key: goal[key] for key in goal})
        current_backwards_node = Node("Goal State.", current_backwards_state, 0)


        init_node = current_node

        distances = {}
        distances[current_node] = 0
        distances[current_backwards_node] = 0

        all_states = set()
        all_states.add(current_state)

        all_backwards_states = set()
        all_backwards_states.add(current_backwards_state)

        # The dictionary that will store the backpointers
        backpointers = {}
        backpointers[current_node] = None
        backpointers[current_backwards_node] = None

        heappush(queue, (current_backwards_node.cost, current_backwards_node, False))
        heappush(queue, (current_node.cost, current_node, True))


        # Implement your search here! Use your heuristic here!
        # When you find a path to the goal return a list of tuples [(state, action)]
        # representing the path. Each element (tuple) of the list represents a state
        # in the path and the action that took you to this state
        #print("Printing the state: {}".format(state))
        #print("Printing the graph: {}".format(graph))
        while time() - start_time < limit and queue:

            if bi_goal(current_state, current_backwards_state):
                backwards_path = reconstruct_path(goal, backpointers, current_backwards_node)
                path = reconstruct_path(init_node, backpointers, current_node)
                backwards_path.reverse()
                path += backwards_path
                return path

            #for cost, node in queue:
            #    print("Name: {}, weight:{}".format(node.name, cost))
            #print()

            cost, node, forward = heappop(queue)


            if forward:
                if is_goal(current_state):
                    print("REACHED THE GOAL")
                    path = reconstruct_path(init_node, backpointers, current_node)
                    return path
                current_node = node
                current_state = node.state
                closed_set.append(current_node)
                for child_node in graph(current_state, all_states):
                    if child_node in closed_set:
                        continue
                    child_node_cost = child_node.cost
                    current_node_cost = distances[current_node]
                    tentative_score = current_node_cost + child_node_cost + heuristic(child_node, current_backwards_state)
                    if child_node not in distances or tentative_score <= distances[child_node]:
                        distances[child_node] = tentative_score
                        if tentative_score == inf:
                            try:
                                queue.remove(child_node)
                            except ValueError:
                                continue
                        else:
                            heappush(queue, (tentative_score, child_node, True))
                    backpointers[child_node] = current_node
                print("Printing current_state in search forward:{}".format(current_state))
            else:
                if reached_ground_zero(current_backwards_state):
                    print("REACHED GROUND ZERO")
                    backwards_path = reconstruct_path(goal, backpointers, current_backwards_node)
                    return backwards_path
                current_backwards_node = node
                current_backwards_state = node.state
                closed_set.append(current_backwards_node)
                for child_node in backwards_graph(current_backwards_state, all_backwards_states):
                    if child_node in closed_set:
                        continue
                    child_node_cost = child_node.cost
                    current_backwards_node_cost = distances[current_backwards_node]
                    tentative_score = current_backwards_node_cost + child_node_cost #+ heuristic(current_backwards_node, current_state)
                    if child_node not in distances or tentative_score <= distances[child_node]:
                        distances[child_node] = tentative_score
                        if tentative_score == inf:
                            try:
                                queue.remove(child_node)
                            except ValueError:
                                print("value error")
                                continue
                        else:
                            heappush(queue, (tentative_score, child_node, False))
                    backpointers[child_node] = current_node
                print("Printing current_state in search backwards:{}".format(current_backwards_state))

        # Failed to find a path
        #print(time() - start_time, 'seconds.')
        print("Failed to find a path from", state, 'within time limit in heuristic.')
        return None


#^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^#
############# END BI DIRECTIONAL A* RELATED FUNCTIONS #######################
#############################################################################



#############################################################################
#################RELAXATION RELATED FUNCTIONS ###############################
#vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv#
# In the end the relaxed search heuristic spent too much time to be useful as a heuristic.
# It might be useful to try it when you decide that the target is close to the

def make_relaxed_effector(rule):
    # Implement a function that returns a function which transitions from state to
    # new_state given the rule. This code runs once, when the rules are constructed
    # before the search is attempted.

    #The effector’s function is
    #to return the state resulting from applying the rule to a given state.
    def relaxed_effect(state):
        # This code is called by graph(state) and runs millions of times
        # Tip: Do something with rule['Produces'] and rule['Consumes'].

        #Copy the state.
        next_state = state.copy()
        produces_list = None
        if "Produces" in rule:
            produces_list = rule["Produces"].items()

        #add the amount of items produced to state.
        if produces_list:
            for produced, amount in produces_list:
                next_state[produced] += amount

        return next_state
    return relaxed_effect

def relaxed_graph(state):
    # Iterates through all recipes/rules, checking which are valid in the given state.
    # If a rule is valid, it returns the rule's name, the resulting state after application

    # to the given state, and the cost for the rule.
    for r in all_recipes:
        if r.check(state):
            effector_wrapper = EffectorWrapper(r.relaxed_effect, r.name, r.cost)
            yield Node(r.name, r.relaxed_effect(state), r.cost, r.relaxed_effect, effector_wrapper)

def relaxed_search(graph, state, is_goal, limit):

        start_time = time()
        queue = []
        closed_set = []

        current_state = state
        current_node = Node("Initial inventory.", current_state, 0)
        init_node = current_node

        distances = {}
        distances[current_node] = 0

        # The dictionary that will store the backpointers
        backpointers = {}
        backpointers[current_node] = None

        for state_node in graph(current_state):
            heappush(queue, (state_node.cost, state_node))
            #print("Printing rule in search: {}".format(recipe))

        # Implement your search here! Use your heuristic here!
        # When you find a path to the goal return a list of tuples [(state, action)]
        # representing the path. Each element (tuple) of the list represents a state
        # in the path and the action that took you to this state
        #print("Printing the state: {}".format(state))
        #print("Printing the graph: {}".format(graph))
        while time() - start_time < limit and queue:

            if is_goal(current_state):
                path = reconstruct_path(init_node, backpointers, current_node)
                return -(len(path) + distances[current_node])

            cost, current_node = heappop(queue)
            current_state = current_node.state
            closed_set.append(current_node)

            for child_node in relaxed_graph(current_state):

                #Lets be safe.
                if child_node in closed_set:
                    continue

                if child_node not in queue:
                    heappush(queue, (child_node.cost, child_node))

                tentative_score = current_node.cost + child_node.cost
                if child_node not in distances or tentative_score <= distances[child_node]:
                    distances[child_node] = tentative_score

                backpointers[child_node] = current_node

            #print("Printing current_state in search:{}".format(current_state))

        # Failed to find a path
        #print(time() - start_time, 'seconds.')
        print("Failed to find a path from", state, 'within time limit in heuristic.')
        return 0

def relaxation_heuristic(state, goal, limit = 0.1): #take goal here.

    heuristic_result = inf
    for product in state.keys():
        if product not in goal.keys() and state[product] >= 1 and product in REQUIRED_ITEMS:
            return heuristic_result
    len_plus_time = relaxed_search(graph, state, is_goal, limit)
    return len_plus_time

#^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^#
################# END OF RELAXATION RELATED FUNCTIONS #######################
#############################################################################

#############################################################################
############## VANILLA SEARCH RELATED FUNCTIONS #############################
#vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv#

def make_checker(rule):
    # Implement a function that returns a function to determine whether a state meets a
    # rule's requirements. This code runs once, when the rules are constructed before
    # the search is attempted.

    #print("Printing rule: {}".format(rule))
    #{'Produces': {'stone_axe': 1}, 'Requires': {'bench': True}, 'Consumes': {'cobble': 3, 'stick': 2}, 'Time': 1}
    #The checker’s role is to assess whether a crafting recipe is valid in a given state.
    #State is the stuff you have.

    #{'bench': True}
    #{'plank': 3, 'stick': 2}
    def check(state):
        # This code is called by graph(state) and runs millions of times.
        # Tip: Do something with rule['Consumes'] and rule['Requires'].

        consumes = None
        requires = None
        if "Consumes" in rule:
            #List of tuples containing the consumed item and how many of is needed.
            consumes = rule["Consumes"].items()
            #List of required items (not consumed)
        if "Requires" in rule:
            requires = rule["Requires"]

        #if it consumes any items
        if consumes:
            #check if we have the consumed items and necesary amount, if not return false
            for consumed, amount in consumes:
                if not (consumed in state and state[consumed] >= amount):
                    return False

        # same as above
        if requires:
            for required in requires:
                if state[required] < 1:
                    return False

        #Reaching here means we have all of what we need
        return True

    return check

def make_effector(rule):
    # Implement a function that returns a function which transitions from state to
    # new_state given the rule. This code runs once, when the rules are constructed
    # before the search is attempted.

    #The effector’s function is
    #to return the state resulting from applying the rule to a given state.
    def effect(state):
        # This code is called by graph(state) and runs millions of times
        # Tip: Do something with rule['Produces'] and rule['Consumes'].


        #Copy the state.
        next_state = state.copy()
        try:
            next_state.total_time_cost += rule["Time"]
            raise
        except AttributeError:

            next_state.total_time_cost = rule["Time"]

        consumes_list = None
        produces_list = None
        if "Consumes" in rule:
            consumes_list = rule["Consumes"].items()
        if "Produces" in rule:
            produces_list = rule["Produces"].items()

        #Update the sate by consuming the amount of items
        if consumes_list:
            for consumed, amount in consumes_list:
                next_state[consumed] -= amount

        #add the amount of items produced to state.
        if produces_list:
            for produced, amount in produces_list:
                next_state[produced] += amount

        return next_state

    return effect

def make_goal_checker(goal):
    # Implement a function that returns a function which checks if the state has
    # met the goal criteria. This code runs once, before the search is attempted.

    def is_goal(state):
        #print("Printing state in is_goal:{}".format(state))
        #print("Printing goal in is_goal:{}".format(goal))
        for item, amount in goal.items():
            #print("Printing item:{}".format(item))
            #print("Printing amount :{}".format(amount))
            if item not in state.keys():
                return False
            elif amount > state[item]:
                return False
        return True

    return is_goal

def graph(current_node, all_states):
    # Iterates through all recipes/rules, checking which are valid in the given state.
    # If a rule is valid, it returns the rule's name, the resulting state after application

    # to the given state, and the cost for the rule.
    state = current_node.state
    all_nodes = []
    for r in all_recipes:
        if r.check(state):
            # This ensure we dont go through duplicate paths.
            new_state = r.effect(state)
            if new_state in all_states.keys():
                #print("State cost in allstates: {}\nState cost in current_node:{}".format(all_states[new_state], current_node.total_cost))
                continue
                if all_states[new_state] >= current_node.total_cost:
                    continue
            all_states[r.effect(state)] = current_node.total_cost
            effector_wrapper = EffectorWrapper(r.effect, r.name, r.cost, r.name)
            all_nodes.append(Node(r.name, r.effect(state), r.cost, effector_wrapper))
    return all_nodes

def invalidate_low_tech(current_state, child_action):

    product = list(name_to_produces[child_action].keys())[0]

    #if time permits will automatically generate this.
    action_priority_list = {"punch for wood": 0, "wooden_axe for wood":1, "stone_axe for wood":2,"iron_axe for wood":3,
                     "stone_pickaxe for ore":1, "iron_pickaxe for ore":2,
                     "wooden_pickaxe for coal":0, "stone_pickaxe for coal":1, "iron_pickaxe for coal":2,
                     "wooden_pickaxe for cobble":0,"stone_pickaxe for cobble":1, "iron_pickaxe for cobble":2,
                     }
    try:
        action_priority = action_priority_list[child_action]
    except:
        return False


    axe_priority_list = {"wooden_axe":1, "stone_axe":2, "iron_axe":3}
    pick_axe_priority_list = {"wooden_pickaxe":0,"stone_pickaxe":1, "iron_pickaxe":2}

    available_priority = 0
    if product == "wood":
        for equipment, priority in axe_priority_list.items():
            if equipment in current_state.keys() and current_state[equipment] > 0:
                available_priority = priority if priority > available_priority else available_priority


    #elif product in {"ore", "coal", "cobble"}:
    elif product in {"ore"}:
        for equipment, priority in pick_axe_priority_list.items():
            if equipment in current_state.keys() and current_state[equipment] > 0:
                available_priority = priority if priority > available_priority else available_priority

    if action_priority <  available_priority:
        #print("Current state:{}\nDesired action: {}".format(current_state, child_action))
        return True
    return False

def prune_unnecesary(queue, goal):
    copy_queue = queue.copy()
    print("Found one goal, pruning started")
    counter = 0;
    for _, node in copy_queue:
        for goal_element in goal:
            if node.state[goal_element] == 0:
                try:
                    queue.remove((_, node))
                except:
                    counter += 1
                    pass
    print("Pruning ended with {} exceptions.")
    return



#Takes a state, which is a the inventory.
def heuristic(current_state, child_node, goal, queue): #take goal here.
    child_state = child_node.state
    action_name = child_node.name
    produces = name_to_produces[action_name]

    #print("\nCurrent state: {} \n Child state:{}".format(current_state, child_state))
    if invalidate_low_tech(current_state, action_name):
        return inf

    for product in produces:
        if product in goal.keys() and child_state[product] > goal[product]:
            return inf

        if product in goal.keys():
            #print("Printing product:{}\nChild state:{}\nGoal:{}".format(product,child_state,goal))
            prune_unnecesary(queue, goal)
            return 0

        #If you already have an REQUIRED item, dont do child_state of it
        if product not in goal.keys() and child_state[product] > 1 and product in REQUIRED_ITEMS:
            #print("Triggered required item heuristic for {}".format(product))
            return inf

        if product not in goal.keys() and (product in max_used_count.keys() and current_state[product] >= max_used_count[product]):
            #print("Triggered more than needed heuristic for {} with current amount \
#{} with effect {}".format(product, current_state[product], child_node.effect.recipe_name))
            return inf

        if product == "cobble":
            #If you made all the stone items you need, you dont want more cobble
            stone_items = {"stone_pickaxe", "furnace", "stone_axe"}
            if all(current_state[stone_key] != 0 for stone_key in stone_items ):
                #print("No more cobble needed, ever.")
                return inf

            if current_state["furnace"] != 0 and child_node.state["cobble"] > 3:
                return inf

        if product not in goal.keys() and product in leaf_items:
            return inf

    return 0

def search(graph, state, is_goal, limit, heuristic, goal):

        if is_goal(state):
            return []

        start_time = time()
        queue = []
        closed_set = []

        current_state = state
        current_node = Node("Initial inventory.", current_state, 0)
        init_node = current_node

        distances = {}
        distances[current_node] = 0

        all_states = {}
        all_states[current_state] = 0

        # The dictionary that will store the backpointers
        backpointers = {}
        backpointers[current_node] = None

        current_node.total_cost = current_node.cost
        heappush(queue, (current_node.cost, current_node))

        # Implement your search here! Use your heuristic here!
        # When you find a path to the goal return a list of tuples [(state, action)]
        # representing the path. Each element (tuple) of the list represents a state
        # in the path and the action that took you to this state
        #print("Printing the state: {}".format(state))
        #print("Printing the graph: {}".format(graph))
        while time() - start_time < limit and queue:

            if is_goal(current_state):
                path = reconstruct_path(init_node, backpointers, current_node)
                print(time() - start_time)
                return path

            #for cost, node in queue:
            #    print("Name: {}, weight:{}".format(node.name, cost))
            #print()


            cost, current_node = heappop(queue)
            current_state = current_node.state

            closed_set.append(current_node)

            for child_node in graph(current_node, all_states):
                #Lets be safe.
                if child_node in closed_set:
                    continue
                child_node_cost = child_node.cost
                current_node_cost = distances[current_node]
                tentative_score = current_node_cost + child_node_cost + heuristic(current_state, child_node, goal, queue)
                if child_node not in distances or tentative_score <= distances[child_node]:
                    distances[child_node] = tentative_score
                    if tentative_score == inf:
                        try:
                            queue.remove(child_node)
                        except ValueError:
                            continue
                    else:
                        child_node.total_cost = tentative_score
                        heappush(queue, (tentative_score, child_node))

                backpointers[child_node] = current_node

            #print("Printing current_state in search:{}".format(current_state))

        # Failed to find a path
        print(time() - start_time, 'seconds.')
        print("Failed to find a path from", state, 'within time limit in heuristic.')
        return None

def reconstruct_path(init_node, cameFrom, current_node):
    total_path = [(current_node.state, current_node.effect)]
    while current_node in cameFrom.keys():
        current_node = cameFrom[current_node]
        if(current_node):
            total_path.append((current_node.state, current_node.effect))
    return total_path

#^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^#
################# VANILLA SEARCH RELATED FUNCTIONS ##########################
#############################################################################


# The json file designates the initial state, and the goals.
if __name__ == '__main__':
    with open('crafting.json') as f:
        Crafting = json.load(f)

    REQUIRED_ITEMS = set()
    name_to_produces = {}
    name_to_requires = {}
    #Due to time constraints this bunch is hand coded. If time permits, will update to automatic generation.
    max_used_count = {"wood":1, "plank":4, "stick":2, "cobble":8, "coal":1, "ingot":6, "ore":1}
    leaf_items = {"rail", "cart"}
    # List of items that can be in your inventory:
    #print('All items:', Crafting['Items'])
    #
    # # List of items in your initial inventory with amounts:
    #print('Initial inventory:', Crafting['Initial'])
    #
    # # List of items needed to be in your inventory at the end of the plan:
    #print('Goal:',Crafting['Goal'])
    #
    # # Dict of crafting recipes (each is a dict):
    #print('Example recipe:','craft stone_pickaxe at bench ->',Crafting['Recipes']['craft stone_pickaxe at bench'])

    # Build rules
    all_recipes = []
    all_backwards_recipes = []
    #count = 0
    #Name of the item
    #The recipe (produces, requires, consumes, time
    rules = {}

    COOK_BOOK = []
    for recipe_name, rule in Crafting['Recipes'].items():
        checker = make_checker(rule)
        effector = make_effector(rule)
        relaxed_effector = make_relaxed_effector(rule)
        recipe = Recipe(recipe_name, checker, effector, relaxed_effector, rule['Time'])
        all_recipes.append(recipe)

        b_checker = make_backwards_checker(rule)
        b_effector = make_backwards_effector(rule)
        b_recipe = Recipe(recipe_name, b_checker, b_effector, relaxed_effector, rule['Time'])
        all_backwards_recipes.append(b_recipe)

        name_to_produces[recipe_name] = rule["Produces"]
        try:
            name_to_requires[recipe_name] = rule["Requires"]
        except:
            #print("This item doesnt require anything")
            pass

        newCookBookEntry = create_cookbook_entry(recipe_name, recipe, rule)
        COOK_BOOK.append(newCookBookEntry)

        if isPrimitive(newCookBookEntry):
            newCookBookEntry.updatePath(None)

    updateRequired(COOK_BOOK)


    #print("The for loop ran {} times".format(count))

    # Create a function which checks for the goal
    is_goal = make_goal_checker(Crafting['Goal'])

    # Initialize first state from initial inventory
    init_state = State({key: 0 for key in Crafting['Items']})
    init_state.update(Crafting['Initial'])

    print("This is the current goal: {}".format(Crafting['Goal']))
    #learn_shortest_paths(COOK_BOOK, Crafting['Goal'])
    #final_state = use_paths_get_goal(COOK_BOOK, state, Crafting['Goal'])
    """
    for entry in COOK_BOOK:
        print(entry)
        for step in entry.path:
            print(step)
        print()
    """
    # Search for a solution
    resulting_plan = search(graph, init_state, is_goal, 300, heuristic, Crafting['Goal'])
    #resulting_plan = bi_search(graph, init_state, is_goal, 30, heuristic, Crafting['Goal'])
    #resulting_plan = None
    if resulting_plan:
        # Print resulting plan
        total_cost = 0;
        for state, action in resulting_plan:
            if action: total_cost += action.cost
            print('\t',state)
            print(action)
        print("The path had {} elements with {} cost".format(len(resulting_plan) - 1, total_cost ))
