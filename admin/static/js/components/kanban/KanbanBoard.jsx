/**
 * Agent Kanban Board - Interactive Task Management Dashboard
 * 
 * Features:
 * - Drag-and-drop task management between columns
 * - Real-time updates across all connected clients
 * - Agent workload visualization and availability status
 * - WIP limit enforcement with visual warnings
 * - Task dependency visualization
 * - Performance analytics and metrics
 */

import React, { useState, useEffect, useRef } from 'react';
import { DragDropContext, Droppable, Draggable } from 'react-beautiful-dnd';
import './KanbanBoard.css';

const KanbanBoard = ({ boardId = 'default', websocketUrl }) => {
    const [boardData, setBoardData] = useState({
        columns: ['backlog', 'assigned', 'in_progress', 'review', 'done'],
        tasks: {},
        agents: [],
        metrics: {},
        wip_limits: {}
    });
    const [loading, setLoading] = useState(true);
    const [agents, setAgents] = useState([]);
    const [selectedTask, setSelectedTask] = useState(null);
    const [showCreateModal, setShowCreateModal] = useState(false);
    const [showAnalytics, setShowAnalytics] = useState(false);
    const wsRef = useRef(null);

    // Initialize board data and WebSocket connection
    useEffect(() => {
        loadBoardData();
        loadAgents();
        connectWebSocket();

        return () => {
            if (wsRef.current) {
                wsRef.current.close();
            }
        };
    }, [boardId]);

    const loadBoardData = async () => {
        try {
            const response = await fetch(`/api/kanban/boards/${boardId}?metrics=true`);
            const data = await response.json();
            if (data.board) {
                setBoardData(data.board);
            }
        } catch (error) {
            console.error('Failed to load board data:', error);
        } finally {
            setLoading(false);
        }
    };

    const loadAgents = async () => {
        try {
            const response = await fetch('/api/kanban/agents');
            const data = await response.json();
            if (data.agents) {
                setAgents(data.agents);
            }
        } catch (error) {
            console.error('Failed to load agents:', error);
        }
    };

    const connectWebSocket = () => {
        if (!websocketUrl) return;

        wsRef.current = new WebSocket(websocketUrl);
        
        wsRef.current.onmessage = (event) => {
            const message = JSON.parse(event.data);
            if (message.type === 'kanban_update') {
                handleRealtimeUpdate(message.data);
            }
        };

        wsRef.current.onclose = () => {
            // Reconnect after 3 seconds
            setTimeout(connectWebSocket, 3000);
        };
    };

    const handleRealtimeUpdate = (updateData) => {
        if (updateData.type === 'task_moved') {
            // Update task position in real-time
            setBoardData(prev => {
                const newTasks = { ...prev.tasks };
                const task = findTaskById(updateData.taskId);
                if (task) {
                    // Remove from old column
                    newTasks[task.status] = newTasks[task.status].filter(t => t.id !== updateData.taskId);
                    // Add to new column
                    task.status = updateData.newStatus;
                    newTasks[updateData.newStatus] = [...(newTasks[updateData.newStatus] || []), task];
                }
                return { ...prev, tasks: newTasks };
            });
        }
    };

    const findTaskById = (taskId) => {
        for (const column of Object.keys(boardData.tasks)) {
            const task = boardData.tasks[column].find(t => t.id === taskId);
            if (task) return task;
        }
        return null;
    };

    const handleDragEnd = async (result) => {
        const { destination, source, draggableId } = result;

        if (!destination || 
            (destination.droppableId === source.droppableId && 
             destination.index === source.index)) {
            return;
        }

        const task = findTaskById(draggableId);
        if (!task) return;

        // Check WIP limits
        const newColumn = destination.droppableId;
        const wipLimit = boardData.wip_limits[newColumn];
        if (wipLimit && boardData.tasks[newColumn].length >= wipLimit) {
            alert(`WIP limit reached for ${newColumn} (${boardData.tasks[newColumn].length}/${wipLimit})`);
            return;
        }

        // Optimistic update
        const newTasks = { ...boardData.tasks };
        newTasks[source.droppableId] = newTasks[source.droppableId].filter(t => t.id !== draggableId);
        task.status = newColumn;
        newTasks[newColumn] = [
            ...newTasks[newColumn].slice(0, destination.index),
            task,
            ...newTasks[newColumn].slice(destination.index)
        ];

        setBoardData(prev => ({ ...prev, tasks: newTasks }));

        // Send update to server
        try {
            await fetch(`/api/kanban/tasks/${draggableId}/move`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    status: newColumn,
                    moved_by: 'current_user' // TODO: Get from auth context
                })
            });
        } catch (error) {
            console.error('Failed to move task:', error);
            // Revert optimistic update
            loadBoardData();
        }
    };

    const createTask = async (taskData) => {
        try {
            const response = await fetch('/api/kanban/tasks', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    ...taskData,
                    created_by: 'current_user',
                    board_id: boardId
                })
            });

            if (response.ok) {
                loadBoardData();
                setShowCreateModal(false);
            }
        } catch (error) {
            console.error('Failed to create task:', error);
        }
    };

    const assignTask = async (taskId, agentId) => {
        try {
            await fetch(`/api/kanban/tasks/${taskId}/assign`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    agent_id: agentId,
                    auto_assign: !agentId
                })
            });
            loadBoardData();
        } catch (error) {
            console.error('Failed to assign task:', error);
        }
    };

    const getColumnStyle = (columnId) => {
        const taskCount = boardData.tasks[columnId]?.length || 0;
        const wipLimit = boardData.wip_limits[columnId];
        
        if (wipLimit && taskCount >= wipLimit) {
            return { borderColor: '#ff4757', borderWidth: '2px' };
        } else if (wipLimit && taskCount >= wipLimit * 0.8) {
            return { borderColor: '#ffa502', borderWidth: '2px' };
        }
        
        return {};
    };

    if (loading) {
        return (
            <div className="kanban-loading">
                <div className="spinner"></div>
                <p>Loading Kanban Board...</p>
            </div>
        );
    }

    return (
        <div className="kanban-board">
            <div className="kanban-header">
                <h1>{boardData.name}</h1>
                <div className="kanban-actions">
                    <button 
                        className="btn btn-primary"
                        onClick={() => setShowCreateModal(true)}
                    >
                        Create Task
                    </button>
                    <button 
                        className="btn btn-secondary"
                        onClick={() => setShowAnalytics(!showAnalytics)}
                    >
                        {showAnalytics ? 'Hide' : 'Show'} Analytics
                    </button>
                    <button className="btn btn-secondary" onClick={loadBoardData}>
                        Refresh
                    </button>
                </div>
            </div>

            {showAnalytics && (
                <KanbanAnalytics metrics={boardData.metrics} />
            )}

            <div className="agents-panel">
                <h3>Active Agents ({agents.filter(a => a.status === 'active').length})</h3>
                <div className="agents-grid">
                    {agents.map(agent => (
                        <AgentCard key={agent.id} agent={agent} />
                    ))}
                </div>
            </div>

            <DragDropContext onDragEnd={handleDragEnd}>
                <div className="kanban-columns">
                    {boardData.columns.map(columnId => {
                        const columnTasks = boardData.tasks[columnId] || [];
                        const wipLimit = boardData.wip_limits[columnId];
                        
                        return (
                            <div 
                                key={columnId} 
                                className="kanban-column"
                                style={getColumnStyle(columnId)}
                            >
                                <div className="column-header">
                                    <h3>{columnId.replace('_', ' ').toUpperCase()}</h3>
                                    <div className="column-meta">
                                        <span className="task-count">{columnTasks.length}</span>
                                        {wipLimit && (
                                            <span className="wip-limit">/ {wipLimit}</span>
                                        )}
                                    </div>
                                </div>

                                <Droppable droppableId={columnId}>
                                    {(provided, snapshot) => (
                                        <div
                                            ref={provided.innerRef}
                                            {...provided.droppableProps}
                                            className={`column-tasks ${snapshot.isDraggingOver ? 'dragging-over' : ''}`}
                                        >
                                            {columnTasks.map((task, index) => (
                                                <Draggable
                                                    key={task.id}
                                                    draggableId={task.id}
                                                    index={index}
                                                >
                                                    {(provided, snapshot) => (
                                                        <TaskCard
                                                            task={task}
                                                            provided={provided}
                                                            snapshot={snapshot}
                                                            agents={agents}
                                                            onAssign={(agentId) => assignTask(task.id, agentId)}
                                                            onClick={() => setSelectedTask(task)}
                                                        />
                                                    )}
                                                </Draggable>
                                            ))}
                                            {provided.placeholder}
                                        </div>
                                    )}
                                </Droppable>
                            </div>
                        );
                    })}
                </div>
            </DragDropContext>

            {showCreateModal && (
                <TaskCreateModal
                    onClose={() => setShowCreateModal(false)}
                    onCreate={createTask}
                    agents={agents}
                />
            )}

            {selectedTask && (
                <TaskDetailModal
                    task={selectedTask}
                    agents={agents}
                    onClose={() => setSelectedTask(null)}
                    onUpdate={loadBoardData}
                />
            )}
        </div>
    );
};

// Task Card Component
const TaskCard = ({ task, provided, snapshot, agents, onAssign, onClick }) => {
    const assignedAgent = agents.find(a => a.id === task.assigned_agent);
    const priorityColors = {
        critical: '#ff3838',
        high: '#ff6b35', 
        medium: '#f7b731',
        low: '#20bf6b'
    };

    return (
        <div
            ref={provided.innerRef}
            {...provided.draggableProps}
            {...provided.dragHandleProps}
            className={`task-card priority-${task.priority} ${snapshot.isDragging ? 'dragging' : ''}`}
            onClick={onClick}
        >
            <div className="task-header">
                <span 
                    className="priority-indicator"
                    style={{ backgroundColor: priorityColors[task.priority] }}
                ></span>
                <h4>{task.title}</h4>
            </div>
            
            {task.description && (
                <p className="task-description">{task.description.substring(0, 100)}...</p>
            )}

            <div className="task-meta">
                {assignedAgent && (
                    <div className="assigned-agent">
                        <img 
                            src={`https://api.dicebear.com/6.x/initials/svg?seed=${assignedAgent.name}`}
                            alt={assignedAgent.name}
                            className="agent-avatar"
                        />
                        <span>{assignedAgent.name}</span>
                    </div>
                )}
                
                {task.estimated_hours && (
                    <span className="time-estimate">{task.estimated_hours}h</span>
                )}
                
                {task.tags && task.tags.length > 0 && (
                    <div className="task-tags">
                        {task.tags.slice(0, 2).map(tag => (
                            <span key={tag} className="task-tag">{tag}</span>
                        ))}
                        {task.tags.length > 2 && <span className="more-tags">+{task.tags.length - 2}</span>}
                    </div>
                )}
            </div>

            {!assignedAgent && task.status === 'backlog' && (
                <button 
                    className="auto-assign-btn"
                    onClick={(e) => {
                        e.stopPropagation();
                        onAssign(null);
                    }}
                >
                    Auto-assign
                </button>
            )}
        </div>
    );
};

// Agent Status Card Component  
const AgentCard = ({ agent }) => {
    const statusColors = {
        active: '#20bf6b',
        busy: '#f7b731', 
        offline: '#95a5a6',
        maintenance: '#e55039'
    };

    const workloadPercentage = (agent.current_workload / agent.max_workload) * 100;

    return (
        <div className="agent-card">
            <div className="agent-header">
                <img 
                    src={`https://api.dicebear.com/6.x/initials/svg?seed=${agent.name}`}
                    alt={agent.name}
                    className="agent-avatar"
                />
                <div className="agent-info">
                    <h4>{agent.name}</h4>
                    <span 
                        className="agent-status"
                        style={{ color: statusColors[agent.status] }}
                    >
                        {agent.status}
                    </span>
                </div>
            </div>
            
            <div className="workload-bar">
                <div 
                    className="workload-fill"
                    style={{ 
                        width: `${workloadPercentage}%`,
                        backgroundColor: workloadPercentage > 80 ? '#e55039' : '#20bf6b'
                    }}
                ></div>
                <span className="workload-text">
                    {agent.current_workload}/{agent.max_workload}
                </span>
            </div>

            {agent.capabilities && agent.capabilities.length > 0 && (
                <div className="agent-capabilities">
                    {agent.capabilities.slice(0, 3).map(cap => (
                        <span key={cap.name} className="capability-tag">
                            {cap.name} ({cap.level})
                        </span>
                    ))}
                </div>
            )}
        </div>
    );
};

// Analytics Panel Component
const KanbanAnalytics = ({ metrics }) => {
    if (!metrics) return null;

    return (
        <div className="kanban-analytics">
            <div className="metrics-grid">
                <div className="metric-card">
                    <h4>Cycle Time</h4>
                    <span className="metric-value">
                        {metrics.avg_cycle_time_hours?.toFixed(1) || 0}h
                    </span>
                </div>
                <div className="metric-card">
                    <h4>Weekly Throughput</h4>
                    <span className="metric-value">{metrics.weekly_throughput || 0}</span>
                </div>
                <div className="metric-card">
                    <h4>Active Tasks</h4>
                    <span className="metric-value">
                        {(metrics.status_counts?.in_progress || 0) + (metrics.status_counts?.assigned || 0)}
                    </span>
                </div>
                <div className="metric-card">
                    <h4>Completed</h4>
                    <span className="metric-value">{metrics.status_counts?.done || 0}</span>
                </div>
            </div>
        </div>
    );
};

// Task Creation Modal Component  
const TaskCreateModal = ({ onClose, onCreate, agents }) => {
    const [formData, setFormData] = useState({
        title: '',
        description: '',
        priority: 'medium',
        estimated_hours: '',
        tags: '',
        assigned_agent: ''
    });

    const handleSubmit = (e) => {
        e.preventDefault();
        const taskData = {
            ...formData,
            tags: formData.tags.split(',').map(t => t.trim()).filter(t => t),
            estimated_hours: formData.estimated_hours ? parseInt(formData.estimated_hours) : null,
            assigned_agent: formData.assigned_agent || null
        };
        onCreate(taskData);
    };

    return (
        <div className="modal-overlay" onClick={onClose}>
            <div className="modal-content" onClick={e => e.stopPropagation()}>
                <div className="modal-header">
                    <h3>Create New Task</h3>
                    <button className="modal-close" onClick={onClose}>&times;</button>
                </div>

                <form onSubmit={handleSubmit}>
                    <div className="form-group">
                        <label>Title</label>
                        <input
                            type="text"
                            required
                            value={formData.title}
                            onChange={e => setFormData({...formData, title: e.target.value})}
                        />
                    </div>

                    <div className="form-group">
                        <label>Description</label>
                        <textarea
                            rows={4}
                            value={formData.description}
                            onChange={e => setFormData({...formData, description: e.target.value})}
                        />
                    </div>

                    <div className="form-row">
                        <div className="form-group">
                            <label>Priority</label>
                            <select
                                value={formData.priority}
                                onChange={e => setFormData({...formData, priority: e.target.value})}
                            >
                                <option value="low">Low</option>
                                <option value="medium">Medium</option>
                                <option value="high">High</option>
                                <option value="critical">Critical</option>
                            </select>
                        </div>

                        <div className="form-group">
                            <label>Estimated Hours</label>
                            <input
                                type="number"
                                min="1"
                                value={formData.estimated_hours}
                                onChange={e => setFormData({...formData, estimated_hours: e.target.value})}
                            />
                        </div>
                    </div>

                    <div className="form-group">
                        <label>Assign to Agent</label>
                        <select
                            value={formData.assigned_agent}
                            onChange={e => setFormData({...formData, assigned_agent: e.target.value})}
                        >
                            <option value="">Auto-assign</option>
                            {agents.filter(a => a.status === 'active').map(agent => (
                                <option key={agent.id} value={agent.id}>
                                    {agent.name} ({agent.current_workload}/{agent.max_workload})
                                </option>
                            ))}
                        </select>
                    </div>

                    <div className="form-group">
                        <label>Tags (comma-separated)</label>
                        <input
                            type="text"
                            placeholder="bug, feature, urgent"
                            value={formData.tags}
                            onChange={e => setFormData({...formData, tags: e.target.value})}
                        />
                    </div>

                    <div className="modal-actions">
                        <button type="button" className="btn btn-secondary" onClick={onClose}>
                            Cancel
                        </button>
                        <button type="submit" className="btn btn-primary">
                            Create Task
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
};

// Task Detail Modal Component
const TaskDetailModal = ({ task, agents, onClose, onUpdate }) => {
    const assignedAgent = agents.find(a => a.id === task.assigned_agent);

    return (
        <div className="modal-overlay" onClick={onClose}>
            <div className="modal-content task-detail-modal" onClick={e => e.stopPropagation()}>
                <div className="modal-header">
                    <h3>{task.title}</h3>
                    <button className="modal-close" onClick={onClose}>&times;</button>
                </div>

                <div className="task-detail-content">
                    <div className="task-meta-detailed">
                        <span className={`priority-badge priority-${task.priority}`}>
                            {task.priority.toUpperCase()}
                        </span>
                        <span className={`status-badge status-${task.status}`}>
                            {task.status.replace('_', ' ').toUpperCase()}
                        </span>
                    </div>

                    <div className="task-description-full">
                        <h4>Description</h4>
                        <p>{task.description || 'No description provided'}</p>
                    </div>

                    {assignedAgent && (
                        <div className="assigned-agent-detail">
                            <h4>Assigned Agent</h4>
                            <AgentCard agent={assignedAgent} />
                        </div>
                    )}

                    <div className="task-timeline">
                        <h4>Timeline</h4>
                        <p>Created: {new Date(task.created_at).toLocaleString()}</p>
                        <p>Updated: {new Date(task.updated_at).toLocaleString()}</p>
                        {task.due_date && <p>Due: {new Date(task.due_date).toLocaleString()}</p>}
                    </div>

                    {task.tags && task.tags.length > 0 && (
                        <div className="task-tags-detail">
                            <h4>Tags</h4>
                            {task.tags.map(tag => (
                                <span key={tag} className="task-tag">{tag}</span>
                            ))}
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
};

export default KanbanBoard;