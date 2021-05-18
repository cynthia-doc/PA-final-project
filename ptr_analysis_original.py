import sys

sys.path.extend(['.', '..'])

from pycparser import c_parser, c_ast

text = r"""
    void foo(int p){
        int* x = malloc(sizeof(int));
        int* y = malloc(sizeof(int));
        int* z = malloc(sizeof(int));

        int* a;
        a = &x;

        int* b = &y;


        if (p == 1) {
            y = &z;
        }
    }
"""

parser = c_parser.CParser()
ast = parser.parse(text, filename='<none>')

var_to_node = dict()
node_to_node = dict()
refnum = 0


def combine_node(curr_node, new_node):
    if curr_node is None:
        return new_node
    if new_node is None:
        return curr_node
    if curr_node == new_node:
        return curr_node
    combined_node = min(curr_node, new_node)
    abandoned_node = max(curr_node, new_node)
    for var, node in var_to_node.items():
        if node == abandoned_node:
            var_to_node[var] = combined_node
    for var, node in node_to_node.items():
        if node == abandoned_node:
            node_to_node[var] = combined_node

    if new_node in node_to_node or curr_node in node_to_node:
        new_dest = combine_node(node_to_node.get(curr_node), node_to_node.get(new_node))
        node_to_node[combined_node] = new_dest

    node_to_node.pop(abandoned_node, None)
    return combined_node


def insert_node(src, dest, dest_is_var):
    global refnum
    # Decl case
    if not (src in var_to_node):
        var_to_node[src] = refnum
        if dest_is_var:
            dest_node = var_to_node[dest]
        else:
            dest_node = dest
        node_to_node[refnum] = dest_node
        refnum += 1
    else:
        curr_pointed = node_to_node[var_to_node[src]]
        if dest_is_var:
            dest_node = var_to_node[dest]
        else:
            dest_node = dest
        new_dest = combine_node(curr_pointed, dest_node)
        node_to_node[var_to_node[src]] = new_dest


# requires stmt to be children of Decl
def is_malloc(stmt):
    if type(stmt[1][1]) == c_ast.FuncCall:
        func_children = stmt[1][1].children()
        if len(func_children) > 1 and len(func_children[1]) > 1:
            func = func_children[0][1].name
            if func == "malloc":
                return True
    return False


def is_addrof(stmt):
    if type(stmt[1][1]) == c_ast.UnaryOp and stmt[1][1].op == "&":
        return True
    return False


def is_deref(stmt):
    if type(stmt[1][1]) == c_ast.UnaryOp and stmt[1][1].op == "*":
        return True
    return False


def analyze_decl(decl):
    global refnum
    if type(decl) == c_ast.Decl and len(decl.children()) > 1:
        decl_child = decl.children()
        if type(decl_child[0][1]) == c_ast.PtrDecl:
            dest = ""
            if is_malloc(decl_child):
                loc = decl.coord.line
                dest = "l_" + str(loc)
                var_to_node[dest] = refnum
                node_to_node[refnum + 1] = refnum
                refnum += 1
                var_to_node[decl.name] = refnum
                refnum += 1
            elif is_addrof(decl_child):
                dest = (decl_child[1][1].expr.name)
                insert_node(decl.name, dest, True)
            elif is_deref(decl_child):
                deref_var = (decl_child[1][1].expr.name)
                dest_node = node_to_node[node_to_node[var_to_node[deref_var]]]
                insert_node(decl.name, dest_node, False)
            elif type(decl_child[1][1]) == c_ast.ID:
                dest_var = decl_child[1][1].name
                dest_node = node_to_node[var_to_node[dest_var]]
                insert_node(decl.name, dest_node, False)


def analyze_assign(assign):
    global refnum
    if type(assign) == c_ast.Assignment and len(assign.children()) > 1:
        assign_child = assign.children()
        if type(assign_child[0][1]) == c_ast.ID:
            lhs = assign_child[0][1].name
            rhs = assign_child[1]
            dest = ""
            if is_addrof(assign_child):
                dest = rhs[1].expr.name
                insert_node(lhs, dest, True)
            elif is_deref(assign_child):
                deref_var = (rhs[1].expr.name)
                dest_node = node_to_node[node_to_node[var_to_node[deref_var]]]
                insert_node(lhs, dest_node, False)
            elif type(rhs[1]) == c_ast.ID:
                dest_var = rhs[1].name
                dest_node = node_to_node[var_to_node[dest_var]]
                insert_node(lhs, dest_node, False)
        elif type(assign_child[0][1]) == c_ast.UnaryOp and assign_child[0][1].op == "*":
            lhs = assign_child[0][1].expr.name
            lhs_node = node_to_node[node_to_node[var_to_node[lhs]]]
            if is_addrof(assign_child):
                dest = rhs[1].expr.name
                combine_node(lhs_node, node_to_node[dest])
            elif is_deref(assign_child):
                deref_var = (rhs[1].expr.name)
                dest_node = node_to_node[node_to_node[var_to_node[deref_var]]]
                insert_node(lhs_node, dest_node)
            elif type(rhs[1]) == c_ast.ID:
                dest_var = rhs[1].name
                dest_node = node_to_node[var_to_node[dest_var]]
                insert_node(lhs_node, dest_node)


for globl_comp in ast.ext:
    if type(globl_comp) == c_ast.FuncDef:
        body = globl_comp.body
        for decl in body.block_items:
            if type(decl) == c_ast.Decl:
                analyze_decl(decl)
            elif type(decl) == c_ast.Assignment:
                analyze_assign(decl)
            elif type(decl) == c_ast.If or type(decl) == c_ast.DoWhile or type(decl) == c_ast.While:
                for component in decl.children():
                    if type(component[1]) == c_ast.Compound:
                        for child in component[1].children():
                            stmt = child[1]
                            if type(stmt) == c_ast.Decl:
                                analyze_decl(stmt)
                            elif type(stmt) == c_ast.Assignment:
                                analyze_assign(stmt)


print(var_to_node)
print(node_to_node)
