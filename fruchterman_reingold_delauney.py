#!/usr/bin/env python
# - coding: utf-8 -
# Copyright (C) 2010 Toms Bauģis <toms.baugis at gmail.com>

"""
 Crossing the FDL with delauney triangulation. Right now does not scale at all
 and the drag is broken.
"""


import gtk
from lib import graphics
from lib.pytweener import Easing

import math
from random import random, randint
from copy import deepcopy

from lib.euclid import Vector2
import itertools

EPSILON = 0.00001

class Node(object):
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.vx = 0
        self.vy = 0
        self.fixed = False #to pin down
        self.cluster = None
        self.neighbours = []


class Graph(object):
    """graph lives on it's own, separated from display"""
    def __init__(self, area_w, area_h):
        self.nodes = []
        self.edges = []
        self.clusters = []
        self.iteration = 0
        self.force_constant = 0
        self.init_layout(area_w, area_h)
        self.graph_bounds = None

    def populate_nodes(self, area_w, area_h):
        self.nodes, self.edges, self.clusters = [], [], []

        # nodes
        for i in range(randint(5, 30)):
            x, y = area_w / 2, area_h / 2
            scale_w = x * 0.2;
            scale_h = y * 0.2

            node = Node(x + (random() - 0.5) * 2 * scale_w,
                        y + (random() - 0.5) * 2 * scale_h)
            self.nodes.append(node)

        # edges
        node_count = len(self.nodes) - 1

        for i in range(randint(node_count / 3, node_count)):  #connect random nodes
            idx1, idx2 = randint(0, node_count), randint(0, node_count)
            node1 = self.nodes[idx1]
            node2 = self.nodes[idx2]

            self.add_edge(node1, node2)

    def add_edge(self, node, node2):
        if node == node2 or (node, node2) in self.edges or (node2, node) in self.edges:
            return

        self.edges.append((node, node2))
        node.neighbours.append(node2)
        node2.neighbours.append(node)

    def remove_edge(self, node, node2):
        if (node, node2) in self.edges:
            self.edges.remove((node, node2))
            node.neighbours.remove(node2)
            node2.neighbours.remove(node)

    def init_layout(self, area_w, area_h):
        if not self.nodes:
            self.nodes.append(Node(area_w / 2, area_h / 2))

        # cluster
        self.clusters = []
        for node in self.nodes:
            node.cluster = None

        all_nodes = list(self.nodes)

        def set_cluster(node, cluster):
            if not node.cluster:
                node.cluster = cluster
                cluster.append(node)
                all_nodes.remove(node)
                for node2 in node.neighbours:
                    set_cluster(node2, cluster)

        while all_nodes:
            node = all_nodes[0]
            if not node.cluster:
                new_cluster = []
                self.clusters.append(new_cluster)
                set_cluster(node, new_cluster)
        # init forces
        self.force_constant = math.sqrt(area_h * area_w / float(len(self.nodes)))
        self.temperature = (len(self.nodes) + math.floor(math.sqrt(len(self.edges)))) * 1
        self.minimum_temperature = 1
        self.initial_temperature = self.temperature
        self.iteration = 0


    def update(self, area_w, area_h):
        self.node_repulsion()
        self.atraction()
        self.cluster_repulsion()
        self.position()

        self.iteration +=1
        self.temperature = max(self.temperature - (self.initial_temperature / 100), self.minimum_temperature)


        # update temperature every ten iterations
        if self.iteration % 10 == 0:
            min_x, min_y, max_x, max_y = self.graph_bounds

            graph_w, graph_h = max_x - min_x, max_y - min_y
            graph_magnitude = math.sqrt(graph_w * graph_w + graph_h * graph_h)
            canvas_magnitude = math.sqrt(area_w * area_w + area_h * area_h)

            self.minimum_temperature = graph_magnitude / canvas_magnitude

    def cluster_repulsion(self):
        """push around unconnected nodes on overlap"""
        for cluster in self.clusters:
            ax1, ay1, ax2, ay2 = self.bounds(cluster)

            for cluster2 in self.clusters:
                if cluster == cluster2:
                    continue

                bx1, by1, bx2, by2 = self.bounds(cluster2)

                if (bx1 <= ax1 <= bx2 or bx1 <= ax2 <= bx2) \
                and (by1 <= ay1 <= by2 or by1 <= ay2 <= by2):

                    dx = (ax1 + ax2) / 2 - (bx1 + bx2) / 2
                    dy = (ay1 + ay2) / 2 - (by1 + by2) / 2

                    max_d = float(max(abs(dx), abs(dy)))

                    dx, dy = dx / max_d, dy / max_d

                    force_x = dx * random() * 100
                    force_y = dy * random() * 100

                    for node in cluster:
                        node.x += force_x
                        node.y += force_y

                    for node in cluster2:
                        node.x -= force_x
                        node.y -= force_y

    def node_repulsion(self):
        """calculate repulsion for the node"""

        for node in self.nodes:
            node.vx, node.vy = 0, 0 # reset velocity back to zero

            for node2 in node.cluster:
                if node == node2: continue

                dx = node.x - node2.x
                dy = node.y - node2.y

                magnitude = math.sqrt(dx * dx + dy * dy)


                if magnitude:
                    force = self.force_constant * self.force_constant / magnitude
                    node.vx += dx / magnitude * force
                    node.vy += dy / magnitude * force



    def atraction(self):
        for edge in self.edges:
            node1, node2 = edge

            dx = node1.x - node2.x
            dy = node1.y - node2.y

            distance = math.sqrt(dx * dx + dy * dy)
            if distance:
                force = distance * distance / self.force_constant

                node1.vx -= dx / distance * force
                node1.vy -= dy / distance * force

                node2.vx += dx / distance * force
                node2.vy += dy / distance * force



    def position(self):
        biggest_move = -1

        x1, y1, x2, y2 = 100000, 100000, -100000, -100000

        for node in self.nodes:
            if node.fixed:
                node.fixed = False
                continue

            distance = math.sqrt(node.vx * node.vx + node.vy * node.vy)

            if distance:
                node.x += node.vx / distance * min(abs(node.vx), self.temperature)
                node.y += node.vy / distance * min(abs(node.vy), self.temperature)

            x1, y1 = min(x1, node.x), min(y1, node.y)
            x2, y2 = max(x2, node.x), max(y2, node.y)

        self.graph_bounds = (x1,y1,x2,y2)

    def bounds(self, nodes):
        x1, y1, x2, y2 = 100000, 100000, -100000, -100000
        for node in nodes:
            x1, y1 = min(x1, node.x), min(y1, node.y)
            x2, y2 = max(x2, node.x), max(y2, node.y)

        return (x1, y1, x2, y2)



class DisplayNode(graphics.Sprite):
    def __init__(self, x, y, real_node):
        graphics.Sprite.__init__(self)

        self.x = x
        self.y = y
        self.real_node = real_node
        self.pivot_x = 5
        self.pivot_y = 5
        self.interactive = True
        self.draggable = True
        self.fill = "#999"

        self.connect("on-mouse-over", self.on_mouse_over)
        self.connect("on-mouse-out", self.on_mouse_out)
        self.draw_graphics()

    def on_mouse_over(self, sprite):
        self.fill = "#000"
        self.draw_graphics()

    def on_mouse_out(self, sprite):
        self.fill = "#999"
        self.draw_graphics()


    def draw_graphics(self):
        self.graphics.clear()
        self.graphics.set_color(self.fill)
        self.graphics.arc(5, 5, 5, 0, math.pi * 2)
        self.graphics.fill()

        # adding invisible circle with bigger radius for easier targeting
        self.graphics.set_color("#000", 0)
        self.graphics.arc(5, 5, 10, 0, math.pi * 2)
        self.graphics.stroke()



class Canvas(graphics.Scene):
    def __init__(self):
        graphics.Scene.__init__(self)
        self.edge_buffer = []
        self.clusters = []

        self.connect("on-enter-frame", self.on_enter_frame)
        self.connect("on-finish-frame", self.on_finish_frame)
        self.connect("on-click", self.on_node_click)
        self.connect("on-drag", self.on_node_drag)
        self.connect("mouse-move", self.on_mouse_move)

        self.mouse_node = None
        self.mouse = None
        self.graph = None
        self.redo_layout = False
        self.display_nodes = []


    def on_node_click(self, scene, event,  sprite):
        new_node = Node(*self.screen_to_graph(event.x, event.y))
        self.graph.nodes.append(new_node)
        display_node = self.add_node(event.x, event.y, new_node)

        self.queue_relayout()

    def on_node_drag(self, scene, node, coords):
        node.real_node.x, node.real_node.y = self.screen_to_graph(*coords)
        node.real_node.fixed = True
        self.redraw_canvas()


    def on_mouse_move(self, scene, event):
        self.mouse = (event.x, event.y)
        self.queue_relayout()



    def triangle_circumcenter(self, a, b, c):
        """shockingly, the circumcenter math has been taken from wikipedia
           we move the triangle to 0,0 coordinates to simplify math"""

        p_a = Vector2(a.x, a.y)
        p_b = Vector2(b.x, b.y) - p_a
        p_c = Vector2(c.x, c.y) - p_a

        p_b2 = p_b.magnitude_squared()
        p_c2 = p_c.magnitude_squared()

        d = 2 * (p_b.x * p_c.y - p_b.y * p_c.x)

        if d < 0:
            d = min(d, EPSILON)
        else:
            d = max(d, EPSILON)


        centre_x = (p_c.y * p_b2 - p_b.y * p_c2) / d
        centre_y = (p_b.x * p_c2 - p_c.x * p_b2) / d

        centre = p_a + Vector2(centre_x, centre_y)
        return centre


    def delauney(self):
        segments = []
        combos = list(itertools.combinations(self.graph.nodes, 3))
        #print "combinations: ", len(combos)
        for a, b, c in combos:
            centre = self.triangle_circumcenter(a, b, c)

            distance2 = (Vector2(a.x, a.y) - centre).magnitude_squared()

            smaller_found = False
            for node in self.graph.nodes:
                if node in [a,b,c]:
                    continue

                if (Vector2(node.x, node.y) - centre).magnitude_squared() < distance2:
                    smaller_found = True
                    break

            if not smaller_found:
                segments.extend(list(itertools.combinations([a,b,c], 2)))

        for segment in segments:
            order = sorted(segment, key = lambda node: node.x+node.y)
            segment = (order[0], order[1])

        segments = set(segments)

        return segments



    def add_node(self, x, y, real_node):
        display_node = DisplayNode(x, y, real_node)
        self.add_child(display_node)
        self.display_nodes.append(display_node)
        return display_node


    def new_graph(self):
        self.clear()
        self.display_nodes = []
        self.add_child(graphics.Label("Click on screen to add nodes. After that you can drag them around", color="#666", x=10, y=10))


        self.edge_buffer = []

        if not self.graph:
            self.graph = Graph(self.width, self.height)
        else:
            self.graph.populate_nodes(self.width, self.height)
            self.queue_relayout()

        for node in self.graph.nodes:
            self.add_node(node.x, node.y, node)

        self.update_buffer()

        self.redraw_canvas()

    def queue_relayout(self):
        self.redo_layout = True
        self.redraw_canvas()

    def update_buffer(self):
        self.edge_buffer = []

        for edge in self.graph.edges:
            self.edge_buffer.append((
                self.display_nodes[self.graph.nodes.index(edge[0])],
                self.display_nodes[self.graph.nodes.index(edge[1])],
            ))


    def on_finish_frame(self, scene, context):
        if self.mouse_node and self.mouse:
            c_graphics = graphics.Graphics(context)
            c_graphics.set_color("#666")
            c_graphics.move_to(self.mouse_node.x, self.mouse_node.y)
            c_graphics.line_to(*self.mouse)
            c_graphics.stroke()


    def on_enter_frame(self, scene, context):
        c_graphics = graphics.Graphics(context)

        if not self.graph:
            self.new_graph()
            self.graph.update(self.width, self.height)


        if self.redo_layout:
            self.redo_layout = False
            self.graph.init_layout(self.width, self.height)


        #rewire nodes using delauney
        segments = self.delauney()
        if segments:
            self.graph.clusters = []
            self.graph.edges = []
            for node in self.graph.nodes:
                node.cluster = None
                node.neighbours = []

            for node, node2 in segments:
                self.graph.add_edge(node, node2)

            self.update_buffer()

            self.graph.init_layout(self.width, self.height)




        c_graphics.set_line_style(width = 0.5)
        done = abs(self.graph.minimum_temperature - self.graph.temperature) < 0.05

        if not done:
            c_graphics.set_color("#aaa")
        else:
            c_graphics.set_color("#666")

        if not done:
            # then recalculate positions
            self.graph.update(self.width, self.height)

            # find bounds
            min_x, min_y, max_x, max_y = self.graph.graph_bounds

            factor_x = float(self.width) / (max_x - min_x)
            factor_y = float(self.height) / (max_y - min_y)
            factor = min(factor_x, factor_y) * 0.9
            start_x = (self.width - (max_x - min_x) * factor) / 2
            start_y = (self.height - (max_y - min_y) * factor) / 2

            for i, node in enumerate(self.display_nodes):
                self.tweener.killTweensOf(node)
                self.animate(node, dict(x = (self.graph.nodes[i].x - min_x) * factor + start_x,
                                        y = (self.graph.nodes[i].y - min_y) * factor + start_y),
                             easing = Easing.Expo.easeOut,
                             duration = 3,
                             instant = False)



            for edge in self.edge_buffer:
                context.move_to(edge[0].x, edge[0].y)
                context.line_to(edge[1].x, edge[1].y)
            context.stroke()


            self.redraw_canvas()

    def screen_to_graph(self,x, y):
        if len(self.graph.nodes) <= 1:
            return x, y

        min_x, min_y, max_x, max_y = self.graph.graph_bounds

        factor_x = float(self.width) / (max_x - min_x)
        factor_y = float(self.height) / (max_y - min_y)
        factor = min(factor_x, factor_y) * 0.9

        start_x = (self.width - (max_x - min_x) * factor) / 2
        start_y = (self.height - (max_y - min_y) * factor) / 2

        graph_x = (x - self.width / 2) / factor
        graph_y = (y - self.height / 2) / factor

        return graph_x, graph_y

    def graph_to_screen(self,x, y):
        pass


class BasicWindow:
    def __init__(self):
        window = gtk.Window(gtk.WINDOW_TOPLEVEL)
        window.set_size_request(600, 500)
        window.connect("delete_event", lambda *args: gtk.main_quit())

        self.canvas = Canvas()

        box = gtk.VBox()
        box.pack_start(self.canvas)

        """
        hbox = gtk.HBox(False, 5)
        hbox.set_border_width(12)

        box.pack_start(hbox, False)

        hbox.pack_start(gtk.HBox()) # filler
        button = gtk.Button("Random Nodes")
        button.connect("clicked", lambda *args: self.canvas.new_graph())
        hbox.pack_start(button, False)
        """

        window.add(box)
        window.show_all()


if __name__ == "__main__":
    example = BasicWindow()
    gtk.main()
