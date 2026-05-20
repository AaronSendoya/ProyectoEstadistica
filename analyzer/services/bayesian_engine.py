import itertools
import numpy as np
import pandas as pd

class Factor:
    """
    Represents a factor (probability table) over a set of variables.
    """
    def __init__(self, variables, states, table):
        """
        Args:
            variables (list): List of variable names in the factor.
            states (dict): Dictionary mapping each variable name to its list of state names.
            table (dict): Dict mapping tuple of state assignments (in variable order) to a float probability.
                          e.g., {('True', 'False'): 0.8, ...}
        """
        self.variables = list(variables)
        self.states = states
        self.table = table

    def restrict(self, var, value):
        """
        Restricts a variable in this factor to a specific value (applies evidence).
        """
        if var not in self.variables:
            return self  # No change if variable not in this factor

        var_idx = self.variables.index(var)
        new_vars = [v for v in self.variables if v != var]
        new_table = {}

        for assignment, prob in self.table.items():
            if assignment[var_idx] == value:
                new_assignment = tuple(val for idx, val in enumerate(assignment) if idx != var_idx)
                new_table[new_assignment] = prob

        return Factor(new_vars, self.states, new_table)

    def multiply(self, other):
        """
        Multiplies this factor with another factor.
        """
        # Union of variables
        new_vars = list(self.variables)
        for var in other.variables:
            if var not in new_vars:
                new_vars.append(var)

        new_table = {}
        
        # We need to find compatible assignments
        # To do this, let's generate all possible assignments for new_vars
        var_states_list = [self.states[v] for v in new_vars]
        
        for assignment in itertools.product(*var_states_list):
            assign_dict = dict(zip(new_vars, assignment))
            
            # Map assignment to self
            self_assign = tuple(assign_dict[v] for v in self.variables)
            # Map assignment to other
            other_assign = tuple(assign_dict[v] for v in other.variables)
            
            p1 = self.table.get(self_assign, 0.0)
            p2 = other.table.get(other_assign, 0.0)
            
            new_table[assignment] = p1 * p2

        return Factor(new_vars, self.states, new_table)

    def sum_out(self, var):
        """
        Marginalizes (sums out) a variable from the factor.
        """
        if var not in self.variables:
            return self

        var_idx = self.variables.index(var)
        new_vars = [v for v in self.variables if v != var]
        new_table = {}

        for assignment, prob in self.table.items():
            new_assignment = tuple(val for idx, val in enumerate(assignment) if idx != var_idx)
            new_table[new_assignment] = new_table.get(new_assignment, 0.0) + prob

        return Factor(new_vars, self.states, new_table)

    def normalize(self):
        """
        Normalizes the factor so that the sum of all probabilities is 1.0.
        """
        total = sum(self.table.values())
        if total == 0:
            # Avoid division by zero, set uniform distribution
            n = len(self.table)
            new_table = {k: 1.0 / n for k in self.table}
        else:
            new_table = {k: v / total for k, v in self.table.items()}
        return Factor(self.variables, self.states, new_table)


def learn_cpts_from_dataframe(df, nodes, edges):
    """
    Learns CPTs for each node in a Bayesian Network from a pandas DataFrame.
    Args:
        df (pd.DataFrame): Dataframe containing categorical/discretized observations.
        nodes (dict): Node metadata, e.g. {node_name: {states: ['True', 'False']}}
        edges (list): Directed links: [['Parent', 'Child'], ...]
    Returns:
        dict: Node CPTs, e.g. {
            'Child': {
                'variables': ['Child', 'Parent'],
                'table': { ('True', 'True'): 0.8, ... }
            }
        }
    """
    # Build parental relationship dictionary
    parents = {name: [] for name in nodes}
    for parent, child in edges:
        if child in parents and parent in parents:
            parents[child].append(parent)

    cpts = {}

    for node_name, node_info in nodes.items():
        node_states = node_info['states']
        node_parents = parents[node_name]
        
        # Variables in this factor: Child first, then parents (standard order)
        factor_vars = [node_name] + node_parents
        
        # Verify that columns exist in dataframe
        missing_cols = [v for v in factor_vars if v not in df.columns]
        if missing_cols:
            # If missing columns, we'll initialize uniform table as fallback
            cpts[node_name] = make_uniform_cpt(node_name, node_parents, nodes)
            continue

        # Get unique states from metadata or auto-infer from dataframe
        states_dict = {v: nodes[v]['states'] for v in factor_vars}
        
        # Initialize tables
        table = {}
        
        # Construct combinations of variables
        combinations = list(itertools.product(*[states_dict[v] for v in factor_vars]))
        
        # Calculate counts
        for combo in combinations:
            assign_dict = dict(zip(factor_vars, combo))
            
            # Apply filters for counts
            query_parts = []
            for col, val in assign_dict.items():
                # Cast val dynamically to match column type if possible
                col_type = df[col].dtype
                if col_type == bool:
                    val_cast = (str(val).lower() in ('true', '1', 'yes'))
                elif col_type == int or col_type == np.int64:
                    try:
                        val_cast = int(val)
                    except:
                        val_cast = val
                elif col_type == float or col_type == np.float64:
                    try:
                        val_cast = float(val)
                    except:
                        val_cast = val
                else:
                    val_cast = str(val)
                
                query_parts.append((col, val_cast))
            
            # Filter rows
            filtered_df = df
            for col, val_cast in query_parts:
                filtered_df = filtered_df[filtered_df[col] == val_cast]
                
            count_combo = len(filtered_df)
            
            # For conditional probability, we need the parent counts
            if node_parents:
                parent_filtered = df
                for p_var in node_parents:
                    p_val = assign_dict[p_var]
                    # Cast parent val
                    p_type = df[p_var].dtype
                    if p_type == bool:
                        p_val_cast = (str(p_val).lower() in ('true', '1', 'yes'))
                    elif p_type == int or p_type == np.int64:
                        try: p_val_cast = int(p_val)
                        except: p_val_cast = p_val
                    elif p_type == float or p_type == np.float64:
                        try: p_val_cast = float(p_val)
                        except: p_val_cast = p_val
                    else:
                        p_val_cast = str(p_val)
                    parent_filtered = parent_filtered[parent_filtered[p_var] == p_val_cast]
                
                count_parents = len(parent_filtered)
            else:
                count_parents = len(df)
                
            # Compute probability
            prob = (count_combo / count_parents) if count_parents > 0 else (1.0 / len(node_states))
            table[combo] = prob
            
        cpts[node_name] = {
            'variables': factor_vars,
            'table': table
        }
        
    return cpts


def make_uniform_cpt(node_name, parents, nodes):
    """
    Creates a uniform CPT table as a fallback.
    """
    factor_vars = [node_name] + parents
    states_dict = {v: nodes[v]['states'] for v in factor_vars}
    
    combinations = list(itertools.product(*[states_dict[v] for v in factor_vars]))
    prob = 1.0 / len(nodes[node_name]['states'])
    table = {combo: prob for combo in combinations}
    
    return {
        'variables': factor_vars,
        'table': table
    }


def run_variable_elimination(nodes, edges, cpts, evidence, target):
    """
    Runs the exact Variable Elimination algorithm to compute P(Target | Evidence).
    Args:
        nodes (dict): {node_name: {states: ['True', 'False']}}
        edges (list): [['Parent', 'Child'], ...]
        cpts (dict): {node_name: {'variables': [...], 'table': {tuple: prob}}}
        evidence (dict): {observed_node: observed_value}
        target (str): name of target variable
    Returns:
        dict: probability distribution of target, e.g. {'True': 0.85, 'False': 0.15}
    """
    # 1. Reconstruct Factor states
    states = {name: info['states'] for name, info in nodes.items()}
    
    # 2. Create factors from CPTs
    factors = []
    for node_name, cpt_info in cpts.items():
        # Handle JSON key parsing: JS stringifies dictionary tuples like "('True', 'False')"
        # We need to make sure cpt_info['table'] maps real tuples to floats
        raw_table = cpt_info['table']
        table = {}
        for k, v in raw_table.items():
            if isinstance(k, str):
                # Parse string tuple e.g. "('True', 'False')" -> ('True', 'False')
                cleaned = k.strip('()')
                tup = tuple(x.strip().replace("'", "").replace('"', '') for x in cleaned.split(','))
                # Single element tuple fix
                if len(tup) == 1 and k.endswith(','):
                    tup = (tup[0],)
                table[tup] = float(v)
            else:
                table[k] = float(v)
                
        factors.append(Factor(cpt_info['variables'], states, table))
        
    # 3. Apply evidence
    for var, val in evidence.items():
        factors = [f.restrict(var, val) for f in factors]
        
    # 4. Eliminate variables
    # Eliminate all variables that are NOT the target and NOT in evidence
    elim_vars = [v for v in nodes if v != target and v not in evidence]
    
    for var in elim_vars:
        # Find factors containing this variable
        var_factors = [f for f in factors if var in f.variables]
        factors = [f for f in factors if var not in f.variables]
        
        if var_factors:
            # Multiply all factors containing var
            joint_factor = var_factors[0]
            for f in var_factors[1:]:
                joint_factor = joint_factor.multiply(f)
                
            # Sum out var
            new_factor = joint_factor.sum_out(var)
            factors.append(new_factor)
            
    # 5. Multiply remaining factors
    if not factors:
        return {s: 1.0 / len(states[target]) for s in states[target]}
        
    final_factor = factors[0]
    for f in factors[1:]:
        final_factor = final_factor.multiply(f)
        
    # 6. Normalize target factor
    normalized = final_factor.normalize()
    
    # 7. Convert table mapping to a clean dictionary
    result = {}
    for assignment, prob in normalized.table.items():
        # assignment will be a 1-tuple containing the value of the target
        val = assignment[0]
        result[val] = round(prob, 4)
        
    return result
