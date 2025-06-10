# simulation/simulation_engine.py
import pandas as pd
import random # For more advanced Monte Carlo if probabilities are not exact numbers

def run_discrete_simulation(transitions, initial_population, num_steps):
    """
    Runs a discrete-event simulation based on given transitions and initial population.
    transitions: List of dictionaries, e.g., [{"source": "Alive", "target": "Dead", "probability": 1.0}]
    initial_population: Dict of initial counts for each state, e.g., {"Alive": 1000, "Dead": 0}
    num_steps: Number of simulation steps.
    Returns a pandas DataFrame of populations at each step.
    """
    # Collect all unique states
    all_states = set(initial_population.keys())
    for t in transitions:
        all_states.add(t["source"])
        all_states.add(t["target"])

    # Initialize current populations, ensuring all states are represented
    current_populations = {state: initial_population.get(state, 0) for state in all_states}

    history_data = []
    history_data.append([0] + [current_populations[s] for s in sorted(all_states)])

    for step in range(1, num_steps + 1):
        next_populations = current_populations.copy() # Start with current populations

        # Reset transitions for this step
        for state in all_states:
            # Accumulate outflow for this step
            outflow_from_state = 0 
            # Create inflows for this step
            inflows_to_state = {s: 0 for s in all_states}

            # Calculate all transitions happening in this step
            # A more sophisticated simulation might track individuals, not just percentages
            # This simple model takes total population and applies probability.

            # Group probabilities by source to ensure sum to 1.0
            grouped_transitions = {}
            for t in transitions:
                if t["source"] not in grouped_transitions:
                    grouped_transitions[t["source"]] = []
                grouped_transitions[t["source"]].append(t)

            for source_node, outgoing_transitions in grouped_transitions.items():
                if current_populations[source_node] > 0:
                    total_population_at_source = current_populations[source_node]

                    # Apply probabilities for each outgoing transition
                    for t in outgoing_transitions:
                        target_node = t["target"]
                        probability = t["probability"]

                        # Calculate number of individuals moving
                        num_moving = total_population_at_source * probability

                        # Distribute this number
                        inflows_to_state[target_node] += num_moving
                        outflow_from_state += num_moving

            # Apply changes to next_populations
            for state in all_states:
                next_populations[state] = (current_populations[state] - (outflow_from_state if state in grouped_transitions else 0)) + inflows_to_state[state]


        current_populations = {s: round(val) for s, val in next_populations.items()} # Round to nearest integer for populations

        history_data.append([step] + [current_populations[s] for s in sorted(all_states)])

    columns = ['Step'] + sorted(list(all_states))
    return pd.DataFrame(history_data, columns=columns)