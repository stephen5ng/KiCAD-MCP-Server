"""
Board size command implementations for KiCAD interface
"""

import pcbnew
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger("kicad_interface")

class BoardSizeCommands:
    """Handles board size operations"""

    def __init__(self, board: Optional[pcbnew.BOARD] = None):
        """Initialize with optional board instance"""
        self.board = board

    def set_board_size(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Set the size of the PCB board by creating edge cuts outline"""
        try:
            if not self.board:
                return {
                    "success": False,
                    "message": "No board is loaded",
                    "errorDetails": "Load or create a board first"
                }

            width = params.get("width")
            height = params.get("height")
            unit = params.get("unit", "mm")

            if width is None or height is None:
                return {
                    "success": False,
                    "message": "Missing dimensions",
                    "errorDetails": "Both width and height are required"
                }

            # Get current board edges bounding box to find the anchor (top-left)
            # This ensures the board resizes relative to its current position
            board_box = self.board.GetBoardEdgesBoundingBox()
            if board_box.GetWidth() > 0:
                anchor_x = board_box.GetX() / 1000000.0
                anchor_y = board_box.GetY() / 1000000.0
            else:
                anchor_x = 0
                anchor_y = 0

            # Clear existing board outline on Edge.Cuts layer
            edge_cuts_id = self.board.GetLayerID("Edge.Cuts")
            
            # Remove drawings (lines, rects, arcs, etc.)
            drawings = self.board.GetDrawings()
            for item in list(drawings):
                if item.GetLayer() == edge_cuts_id:
                    self.board.Remove(item)
            
            # Remove tracks on Edge.Cuts (uncommon but possible)
            for item in list(self.board.GetTracks()):
                if item.GetLayer() == edge_cuts_id:
                    self.board.Remove(item)
            
            # Remove zones on Edge.Cuts (uncommon but possible)
            # KiCad 7.0+ uses Zones() method
            try:
                zones = self.board.Zones()
            except AttributeError:
                # Fallback for older/different SWIG versions if needed
                try:
                    zones = self.board.GetZones()
                except AttributeError:
                    zones = []

            for item in list(zones):
                if item.GetLayer() == edge_cuts_id:
                    self.board.Remove(item)

            # Force rebuild of polygon outlines to refresh internal state
            if hasattr(self.board, "BuildPolygonOutlines"):
                self.board.BuildPolygonOutlines()

            # Create board outline using BoardOutlineCommands
            from commands.board.outline import BoardOutlineCommands
            outline_commands = BoardOutlineCommands(self.board)

            # Create rectangular outline at anchor
            result = outline_commands.add_board_outline({
                "shape": "rectangle",
                "centerX": anchor_x + width / 2,
                "centerY": anchor_y + height / 2,
                "width": width,
                "height": height,
                "unit": unit
            })

            if result.get("success"):
                # Final rebuild after adding new outline
                if hasattr(self.board, "BuildPolygonOutlines"):
                    self.board.BuildPolygonOutlines()
                    
                return {
                    "success": True,
                    "message": f"Board size updated to {width}x{height} {unit} at ({anchor_x}, {anchor_y})",
                    "size": {
                        "width": width,
                        "height": height,
                        "unit": unit
                    },
                    "anchor": {
                        "x": anchor_x,
                        "y": anchor_y,
                        "unit": "mm"
                    }
                }
            else:
                return result

        except Exception as e:
            logger.error(f"Error setting board size: {str(e)}")
            return {
                "success": False,
                "message": "Failed to set board size",
                "errorDetails": str(e)
            }
