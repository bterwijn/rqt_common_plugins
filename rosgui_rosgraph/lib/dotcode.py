# Software License Agreement (BSD License)
#
# Copyright (c) 2008, Willow Garage, Inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
#  * Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
#  * Redistributions in binary form must reproduce the above
#    copyright notice, this list of conditions and the following
#    disclaimer in the documentation and/or other materials provided
#    with the distribution.
#  * Neither the name of Willow Garage, Inc. nor the names of its
#    contributors may be used to endorse or promote products derived
#    from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
# COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

# this is a modified version of rx/rxgraph/src/rxgraph/dotcode.py

import re

import rosgraph.impl.graph

# node/node connectivity
NODE_NODE_GRAPH = 'node_node'
# node/topic connections where an actual network connection exists
NODE_TOPIC_GRAPH = 'node_topic'
# all node/topic connections, even if no actual network connection
NODE_TOPIC_ALL_GRAPH = 'node_topic_all'

import urllib

QUIET_NAMES = ['/diag_agg', '/runtime_logger', '/pr2_dashboard', '/rviz', '/rosout', '/cpu_monitor', '/monitor', '/hd_monitor', '/rxloggerlevel', '/clock']

def matches_any(name, patternlist):
    if patternlist is None or len(patternlist) == 0:
        return False
    for pattern in patternlist:
        if str(name).strip() == pattern:
            return True
        if re.match("^[a-zA-Z0-9_]+$", pattern) is None:
            if re.match(str(pattern), name.strip()) is not None:
                return True
    return False

class RosGraphDotcodeGenerator:

    def __init__(self):
        self.dotcode_factory = None

    def _add_edge(self, edge, dotgraph, is_topic=False):
        if is_topic:
            self.dotcode_factory.add_edge_to_graph(dotgraph, edge.start, edge.end, label = edge.label, url = 'topic:%s' % edge.label)
        else:
            self.dotcode_factory.add_edge_to_graph(dotgraph, edge.start, edge.end, label = edge.label)
            
    def _add_node(self, node, rosgraphinst, dotgraph, quiet):
        if node in rosgraphinst.bad_nodes:
            if quiet:
                return ''
            bn = rosgraphinst.bad_nodes[node]
            if bn.type == rosgraph.impl.graph.BadNode.DEAD:
                self.dotcode_factory.add_node_to_graph(dotgraph,
                                                       nodename = node,
                                                       shape = "doublecircle",
                                                       url=node,
                                                       color = "red")
            else:
                self.dotcode_factory.add_node_to_graph(dotgraph,
                                                       nodename = node,
                                                       shape = "doublecircle",
                                                       url=node,
                                                       color = "orange")
        else:
            self.dotcode_factory.add_node_to_graph(dotgraph,
                                                   nodename = node,
                                                   shape = 'ellipse',
                                                   url=node)
            
    def _add_topic_node(self, node, dotgraph, quiet):
        label = rosgraph.impl.graph.node_topic(node)
        self.dotcode_factory.add_node_to_graph(dotgraph,
                                               nodename = label,
                                               nodelabel = label,
                                               shape = 'box',
                                               url="topic:%s"%label)
    

    def _quiet_filter(self, name):
        # ignore viewers
        for n in QUIET_NAMES:
            if n in name:
                return False
        return True
    
    def _quiet_filter_edge(self, edge):
        for quiet_label in ['/time', '/clock', '/rosout']:
            if quiet_label == edge.label:
                return False
        return self._quiet_filter(edge.start) and self._quiet_filter(edge.end)
    
    def generate_namespaces(self, rosgraph, graph_mode, quiet=False):
        """
        Determine the namespaces of the nodes being displayed
        """
        namespaces = []
        if graph_mode == NODE_NODE_GRAPH:
            nodes = rosgraph.nn_nodes
            if quiet:
                nodes = [n for n in nodes if not n in QUIET_NAMES]
            namespaces = list(set([roslib.names.namespace(n) for n in nodes]))
    
        elif graph_mode == NODE_TOPIC_GRAPH or \
                 graph_mode == NODE_TOPIC_ALL_GRAPH:
            nn_nodes = rosgraph.nn_nodes
            nt_nodes = rosgraph.nt_nodes
            if quiet:
                nn_nodes = [n for n in nn_nodes if not n in QUIET_NAMES]
                nt_nodes = [n for n in nt_nodes if not n in QUIET_NAMES]
            if nn_nodes or nt_nodes:
                namespaces = [roslib.names.namespace(n) for n in nn_nodes]
            # an annoyance with the rosgraph library is that it
            # prepends a space to topic names as they have to have
            # different graph node namees from nodes. we have to strip here
            namespaces.extend([roslib.names.namespace(n[1:]) for n in nt_nodes])

        return list(set(namespaces))
    
    def _filter_edges(self, edges, nodes):
        # currently using and rule as the or rule generates orphan nodes with the current logic
        return [e for e in edges if e.start in nodes and e.end in nodes]
    
    
    def generate_dotcode(self,
                         rosgraphinst,
                         ns_filter,
                         topic_filter,
                         graph_mode,
                         dotcode_factory,
                         hide_single_connection_topics = False,
                         hide_dead_end_topics = False,
                         cluster_namespaces_level = 0,
                         accumulate_actions = True,
                         orientation = 'LR',
                         rank = 'same',   # None, same, min, max, source, sink
                         ranksep = 0.2,   # vertical distance between layers
                         rankdir = 'TB',  # direction of layout (TB top > bottom, LR left > right)
                         simplify = True, # remove double edges
                         quiet=False):
        """
        @param rosgraphinst: RosGraph instance
        @param ns_filter: namespace filter (must be canonicalized with trailing '/')
        @type  ns_filter: string
        @param graph_mode str: NODE_NODE_GRAPH | NODE_TOPIC_GRAPH | NODE_TOPIC_ALL_GRAPH
        @type  graph_mode: str
        @param orientation: rankdir value (see ORIENTATIONS dict)
        @type  dotcode_factory: object
        @param dotcode_factory: abstract factory manipulating dot language objects
        @return: dotcode generated from graph singleton
        @rtype: str
        """
        self.dotcode_factory = dotcode_factory

        includes = []
        excludes = []
        for name in ns_filter.split(','):
            if name.strip().startswith('-'):
                excludes.append(name.strip()[1:])
            else:
                includes.append(name.strip())
        if includes == [] or includes == ['/']:
            includes = ['.*']

        topic_includes = []
        topic_excludes = []
        for name in topic_filter.split(','):
            if name.strip().startswith('-'):
                topic_excludes.append(name.strip()[1:])
            else:
                topic_includes.append(name.strip())
        if topic_includes == [] or topic_includes == ['/']:
            topic_includes = ['.*']
        
        node_connections = {}
        
        nn_nodes = []
        nt_nodes = []
        # create the node definitions
        if graph_mode == NODE_NODE_GRAPH:
            nn_nodes = rosgraphinst.nn_nodes
            if quiet:
                nn_nodes = [n for n in nn_nodes if not n in QUIET_NAMES]
            nn_nodes = [n for n in nn_nodes if matches_any(n, includes) and not matches_any(n, excludes)]
            edges = rosgraphinst.nn_edges
            edges = [e for e in edges if matches_any(e.label, topic_includes) and not matches_any(e.label, topic_excludes)]
            
        elif graph_mode == NODE_TOPIC_GRAPH or \
                 graph_mode == NODE_TOPIC_ALL_GRAPH:
            nn_nodes = rosgraphinst.nn_nodes
            nt_nodes = rosgraphinst.nt_nodes
            if quiet:
                nn_nodes = [n for n in nn_nodes if not n in QUIET_NAMES]
                nt_nodes = [n for n in nt_nodes if not n in QUIET_NAMES]
            nodenames = [str(n) for n in nn_nodes]
            nn_nodes = [n for n in nn_nodes if matches_any(n, includes) and not matches_any(n, excludes)]
            nt_nodes = [n for n in nt_nodes if matches_any(n, topic_includes) and not matches_any(n, topic_excludes)]

            # create the edge definitions
            if graph_mode == NODE_TOPIC_GRAPH:
                edges = rosgraphinst.nt_edges
            else:
                edges = rosgraphinst.nt_all_edges
            
        if quiet:
            edges = filter(self._quiet_filter_edge, edges)

        nodes = list(nn_nodes) + list(nt_nodes)
        edges = self._filter_edges(edges, nodes)

        # for accumulating actions topics
        action_nodes = {}
        
        if graph_mode != NODE_NODE_GRAPH and (accumulate_actions or hide_dead_end_topics or hide_single_connection_topics):
            for edge in edges:
                if not edge.start in node_connections:
                    node_connections[edge.start] = {'outgoing' : [], 'incoming' : []}
                if not edge.end in node_connections:
                    node_connections[edge.end] = {'outgoing' : [], 'incoming' : []}
                node_connections[edge.start]['outgoing'].append(edge)
                node_connections[edge.end]['incoming'].append(edge)

            if hide_dead_end_topics or hide_single_connection_topics:
                removal_nodes = []
                for n in nt_nodes:
                    if n in node_connections:
                        node_edges = []
                        has_out_edges = False
                        if 'outgoing' in node_connections[n]:
                            node_edges.extend(node_connections[n]['outgoing'])
                            if len(node_connections[n]['outgoing']) > 0:
                                has_out_edges = True
                        if 'incoming' in node_connections[n]:
                            node_edges.extend(node_connections[n]['incoming'])
                        if ((hide_single_connection_topics and len(node_edges) < 2) or
                            (hide_dead_end_topics and not has_out_edges)):
                            removal_nodes.append(n)
                            for e in node_edges:
                                if e in edges:
                                    edges.remove(e)
           
                for n in removal_nodes:
                    nt_nodes.remove(n)

            if accumulate_actions:
                removal_nodes = []
                for n in nt_nodes:
                    if str(n).endswith('/feedback'):
                        prefix = str(n)[:-len('/feedback')].strip()
                        action_topic_nodes = []
                        action_topic_edges_out = set()
                        action_topic_edges_in = set()
                        for suffix in ['/status', '/result', '/goal', '/cancel', '/feedback']:
                            for n2 in nt_nodes:
                                if str(n2).strip() == prefix + suffix:
                                    action_topic_nodes.append(n2)
                                    if n2 in node_connections:
                                        action_topic_edges_out.update(node_connections[n2]['outgoing'])
                                        action_topic_edges_in.update(node_connections[n2]['incoming'])
                        if len(action_topic_nodes) == 5:
                            # found action
                            removal_nodes.extend(action_topic_nodes)
                            for e in action_topic_edges_out:
                                if e in edges:
                                    edges.remove(e)
                            for e in action_topic_edges_in:
                                if e in edges:
                                    edges.remove(e)
                            action_nodes[prefix] = {'topics': action_topic_nodes,
                                                    'outgoing': action_topic_edges_out,
                                                    'incoming' : action_topic_edges_in}
                for n in removal_nodes:
                    nt_nodes.remove(n)

        nodenames = [str(n).strip() for n in nn_nodes] + [str(n).strip() for n in nt_nodes]
        edges = [e for e in edges if e.start.strip() in nodenames and e.end.strip() in nodenames]
        
        removal_nodes = []
        for n in nt_nodes:
            keep = False
            for e in edges:
                if (e.start.strip() == str(n).strip() or e.end.strip() == str(n).strip()):
                    keep = True
                    break
            if not keep:
                removal_nodes.append(n)
        for n in removal_nodes:
            nt_nodes.remove(n)
            
        # create the graph
            
        # result = "digraph G {\n  rankdir=%(orientation)s;\n%(nodes_str)s\n%(edges_str)s}\n" % vars()
        dotgraph = dotcode_factory.get_graph(rank = rank,
                                          ranksep = ranksep,
                                          simplify = simplify,
                                          rankdir = orientation)

        namespace_clusters = {}
        if nt_nodes is not None:
            for n in nt_nodes:
                if n in node_connections:
                    # cluster topics with same namespace
                    if (cluster_namespaces_level > 0 and
                        str(n).count('/') > 1 and
                        len(str(n).split('/')[1]) > 0):
                        
                        namespace = str(n).split('/')[1]
                        if namespace not in namespace_clusters:
                            namespace_clusters[namespace] = dotcode_factory.add_subgraph_to_graph(dotgraph, namespace, rank = rank, rankdir = orientation, simplify = simplify)
                        self._add_topic_node(n, dotgraph=namespace_clusters[namespace], quiet=quiet)
                    else:
                        self._add_topic_node(n, dotgraph=dotgraph, quiet=quiet)
                else:
                    self._add_topic_node(n, dotgraph=dotgraph, quiet=quiet)

        if len(action_nodes) > 0:
            for (action_prefix, node_dict) in action_nodes.items():
                n = action_prefix + '/action_topics'
                # add virtual graph nodes for each action
                if (cluster_namespaces_level > 0 and
                    str(n).count('/') > 1 and
                    len(str(n).split('/')[1]) > 0):
                        
                    namespace = str(n).split('/')[1]
                    if namespace not in namespace_clusters:
                        namespace_clusters[namespace] = dotcode_factory.add_subgraph_to_graph(dotgraph, namespace, rank = rank, rankdir = orientation, simplify = simplify)
                    self._add_topic_node(n, dotgraph=namespace_clusters[namespace], quiet=quiet)
                else:
                    self._add_topic_node(n, dotgraph=dotgraph, quiet=quiet)
                        
        # for normal node, if we have created a namespace clusters for
        # one of its peer topics, drop it into that cluster
        if nn_nodes is not None:
            for n in nn_nodes:
                if n in node_connections:
                    if (cluster_namespaces_level > 0 and
                        str(n).count('/') >= 1 and
                        len(str(n).split('/')[1]) > 0 and
                        str(n).split('/')[1] in namespace_clusters):
                        
                        namespace = str(n).split('/')[1]
                        self._add_node(n, rosgraphinst=rosgraphinst, dotgraph=namespace_clusters[namespace], quiet=quiet)
                    else:
                        self._add_node(n, rosgraphinst=rosgraphinst, dotgraph=dotgraph, quiet=quiet)
                else:
                    self._add_node(n, rosgraphinst=rosgraphinst, dotgraph=dotgraph, quiet=quiet)

        for e in edges:
            if (e.start.strip() in nodenames and e.end.strip() in nodenames):
                self._add_edge(e, dotgraph=dotgraph, is_topic=(graph_mode == NODE_NODE_GRAPH))

        if len(action_nodes) > 0:
            for (action_prefix, node_dict) in action_nodes.items():
                if 'outgoing' in node_dict:
                    for out_edge in node_dict['outgoing']:
                        self.dotcode_factory.add_edge_to_graph(dotgraph, action_prefix[1:] + '/action_topics', out_edge.end)
                if 'incoming' in node_dict:
                    for in_edge in node_dict['incoming']:
                        self.dotcode_factory.add_edge_to_graph(dotgraph, in_edge.start, action_prefix[1:] + '/action_topics')
                
        self.dotcode = dotcode_factory.create_dot(dotgraph)
        return self.dotcode
        
      
