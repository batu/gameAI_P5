import json
from collections import namedtuple, defaultdict, OrderedDict
from timeit import default_timer as time
from _heapq import heappop, heappush

Recipe = namedtuple('Recipe', ['name', 'check', 'effect', 'cost'])


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
        diff_keys = set(goal.keys()) - set(state.keys())
        diff_vals = set(goal.values()) - set(state.values())
        #print(diff_keys)
        #print(diff_vals)
        #For some reason == isnt working

        #if there is no difference between current and isgoal we found the goal
        if not diff_keys and not diff_vals:
            print("Goal reached!")
            return True
        return False

    return is_goal


def graph(state):
    # Iterates through all recipes/rules, checking which are valid in the given state.
    # If a rule is valid, it returns the rule's name, the resulting state after application

    # to the given state, and the cost for the rule.
    for r in all_recipes:
        if r.check(state):
            yield (r.name, r.effect(state), r.cost)


def heuristic(state):
    # Implement your heuristic here!
    print("In heuristic.")
    return 0

def search(graph, state, is_goal, limit, heuristic):

    start_time = time()
    path = []


    for recipe in graph(state):
        print("Printing rule in search: {}".format(recipe))

    # Implement your search here! Use your heuristic here!
    # When you find a path to the goal return a list of tuples [(state, action)]
    # representing the path. Each element (tuple) of the list represents a state
    # in the path and the action that took you to this state
    #print("Printing the state: {}".format(state))
    #print("Printing the graph: {}".format(graph))
    while time() - start_time < limit:
        if is_goal(state):
            return path
        continue

    # Failed to find a path
    print(time() - start_time, 'seconds.')
    print("Failed to find a path from", state, 'within time limit.')
    return None


def astar_search(source_point: tuple, source_box: tuple, destination_box: tuple, destination_point:tuple, box_adj_list)-> list:

    # The priority queue
    queue = []

    # The dictionary that will be returned with the costs
    distances = {}
    distances[source_box] = 0

    # The dictionary that will store the backpointers
    backpointers = {}
    backpointers[source_box] = None

    #[box] = points (y,x)
    detail_points = {}
    detail_points[source_box] = source_point

    while queue:
        current_dist, current_box = heappop(queue)

        # Check if current node is the destination
        if current_box == destination_box:

            # List containing all cells from initial_position to destination
            path = [current_box]
            point_path = [detail_points[current_box]]

            # Go backwards from destination until the source using backpointers
            # and add all the nodes in the shortest path into a list
            current_back_node = backpointers[current_box]
            while current_back_node is not None:
                path.append(current_back_node)
                point_path.append(detail_points[current_back_node])
                current_back_node = backpointers[current_back_node]

            point_path.reverse()
            point_path.append(destination_point)

            point_segments = []
            for i in range(0, len(point_path)-1):
                point_segments.append((point_path[i],point_path[i+1]))

            return path[::-1], point_segments

        # Calculate cost from current note to all the adjacent ones
        for adj_box in box_adj_list[current_box]:
            current_point = detail_points[current_box]
            adj_box_point = box_to_point(current_box, adj_box, current_point)
            adj_box_cost = math.sqrt((adj_box_point[0] - current_point[0])**2 + (adj_box_point[1] - current_point[1])**2)
            pathcost = current_dist + adj_box_cost + heuristic(current_point, destination_point)

            # If the cost is new
            if adj_box not in distances or pathcost < distances[adj_box]:
                distances[adj_box] = pathcost
                detail_points[adj_box] = adj_box_point
                backpointers[adj_box] = current_box
                heappush(queue, (pathcost, adj_box))

    return [],[]



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
    for name, rule in Crafting['Recipes'].items():
        checker = make_checker(rule)
        effector = make_effector(rule)
        recipe = Recipe(name, checker, effector, rule['Time'])
        all_recipes.append(recipe)
    #print("The for loop ran {} times".format(count))

    # Create a function which checks for the goal
    is_goal = make_goal_checker(Crafting['Goal'])

    # Initialize first state from initial inventory
    state = State({key: 0 for key in Crafting['Items']})
    state.update(Crafting['Initial'])

    # Search for a solution
    resulting_plan = search(graph, state, is_goal, 5, heuristic)

    if resulting_plan:
        # Print resulting plan
        for state, action in resulting_plan:
            print('\t',state)
            print(action)
