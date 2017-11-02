import json
from collections import namedtuple, defaultdict, OrderedDict
from timeit import default_timer as time
from _heapq import heappop, heappush

Recipe = namedtuple('Recipe', ['name', 'check', 'effect', 'cost'])

#A wrapper functino over effectors in the CookBookEntry representation
#Helps with keeping track of what effector is linked to what and creates what etc.
class EffectorWrapper():
    def __init__(self, effector, name):
        self.effector = effector
        self.creates = name
        #There are some items that are catalysts that you only need one.
        self.required = False

    def __call__(self, *args, **kwargs):
        return self.effector(args[0])

    def __str__(self):
        return str("This is a {} effector.".format(self.creates))

# Node representation for A* to help readability
class Node():
    def __init__(self, name, state, cost):
        self.name = name
        self.state = state
        self.cost = cost

    def __lt__(self, other):
        return self.cost < other.cost

# A datastructure that keeps hold of lots of information regarding cookbook entries
class CookBookEntry():

    def __init__(self, name, cost, effector, requires = None, consumes = None, produces = None):
        self.name = name
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

### The Path Learning Related functions

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
                print("Updated catalyst for {}".format(required_cook_book_entry.name))


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
def create_cookbook_entry(name, recipe, rule):
    newCookBookEntry = CookBookEntry(name, recipe.cost, EffectorWrapper(recipe.effect, name))
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
                if not (required not in state):
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

def graph(state):
    # Iterates through all recipes/rules, checking which are valid in the given state.
    # If a rule is valid, it returns the rule's name, the resulting state after application

    # to the given state, and the cost for the rule.
    for r in all_recipes:
        if r.check(state):
            yield Node(r.name, r.effect(state), r.cost)

#Takes a state, which is a the inventory.
def heuristic(state): #take goal here.

    # check what is the maximum amount of items required to craft another item. (I think it is 6)
    # cutoff_treshold = 6
    # if any item in the goal state.amount is > cutoff_treshold.]
    # cutoff_treshold = amount

    # returnning is a number. 999999999999999999999

    # Implement your heuristic here!
    #print("In heuristic.")
    return 0

def search(graph, state, is_goal, limit, heuristic):

    start_time = time()
    path = []
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
        queue.append(state_node)
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
            return path

        current_node = heappop(queue)
        current_state = current_node.state
        closed_set.append(current_node)

        for child_node in graph(current_state):

            #Lets be safe.
            if child_node in closed_set:
                continue

            if child_node not in queue:
                queue.append(child_node)


            tentative_score = current_node.cost + child_node.cost + heuristic(state)
            if child_node not in distances or tentative_score <= distances[child_node]:
                distances[child_node] = tentative_score

            backpointers[child_node] = current_node

        #print("Printing current_state in search:{}".format(current_state))


    # Failed to find a path
    print(time() - start_time, 'seconds.')
    print("Failed to find a path from", state, 'within time limit.')
    return None

def reconstruct_path(init_node, cameFrom, current_node):
    total_path = [(current_node.state, current_node.name)]
    while current_node in cameFrom.keys():
        current_node = cameFrom[current_node]
        total_path.append((current_node.state, current_node.name))
    total_path.append((init_node.state,init_node.name))
    return total_path


# The json file designates the initial state, and the goals.
if __name__ == '__main__':
    with open('crafting.json') as f:
        Crafting = json.load(f)

    # # List of items that can be in your inventory:
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
    #count = 0
    #Name of the item
    #The recipe (produces, requires, consumes, time
    rules = {}

    COOK_BOOK = []
    for name, rule in Crafting['Recipes'].items():
        checker = make_checker(rule)
        effector = make_effector(rule)
        recipe = Recipe(name, checker, effector, rule['Time'])
        all_recipes.append(recipe)

        newCookBookEntry = create_cookbook_entry(name, recipe, rule)
        COOK_BOOK.append(newCookBookEntry)

        if isPrimitive(newCookBookEntry):
            newCookBookEntry.updatePath(None)

    updateRequired(COOK_BOOK)


    #print("The for loop ran {} times".format(count))

    # Create a function which checks for the goal
    is_goal = make_goal_checker(Crafting['Goal'])

    # Initialize first state from initial inventory
    state = State({key: 0 for key in Crafting['Items']})
    state.update(Crafting['Initial'])

    print("This is the current goal: {}".format(Crafting['Goal']))
    learn_shortest_paths(COOK_BOOK, Crafting['Goal'])
    final_state = use_paths_get_goal(COOK_BOOK, state, Crafting['Goal'])

    # Search for a solution
    #resulting_plan = search(graph, state, is_goal, 30, heuristic)
    resulting_plan = None
    if resulting_plan:
        # Print resulting plan
        for state, action in resulting_plan:
            print('\t',state)
            print(action)
