"use client";
import { useState, useEffect } from 'react';
import { useAuth } from '../../context/AuthContext';
import { fetchWithAuth } from '../../lib/api';
import { useRouter } from 'next/navigation';

export default function Dashboard() {
  const { token, logout } = useAuth();
  const router = useRouter();
  const [tasks, setTasks] = useState([]);
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');

  useEffect(() => {
    if (!token) {
      router.push('/');
    } else {
      loadTasks();
    }
  }, [token, router]);

  const loadTasks = async () => {
    try {
      const data = await fetchWithAuth('/tasks');
      setTasks(data);
    } catch (err) {
      if (err.message.includes('401')) logout();
    }
  };

  const addTask = async (e) => {
    e.preventDefault();
    if (!title.trim()) return;
    try {
      await fetchWithAuth('/tasks', {
        method: 'POST',
        body: JSON.stringify({ title, description }),
      });
      setTitle('');
      setDescription('');
      loadTasks();
    } catch (err) {
      console.error(err);
    }
  };

  const deleteTask = async (id) => {
    try {
      await fetchWithAuth(`/tasks/${id}`, { method: 'DELETE' });
      loadTasks();
    } catch (err) {
      console.error(err);
    }
  };

  if (!token) return null;

  return (
    <div className="container" style={{ marginTop: '4rem' }}>
      <div className="header">
        <h1>My Tasks</h1>
        <button className="btn" style={{ width: 'auto' }} onClick={logout}>Logout</button>
      </div>

      <div className="glass-panel" style={{ maxWidth: '100%', marginBottom: '2rem', padding: '1.5rem' }}>
        <form className="task-form" onSubmit={addTask}>
          <input
            className="input-field"
            style={{ marginBottom: 0, flex: 1 }}
            placeholder="Task title..."
            value={title}
            onChange={(e) => setTitle(e.target.value)}
          />
          <input
            className="input-field"
            style={{ marginBottom: 0, flex: 2 }}
            placeholder="Description (optional)"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
          />
          <button type="submit" className="btn" style={{ width: '150px', marginBottom: 0 }}>
            Add Task
          </button>
        </form>
      </div>

      <div className="task-list">
        {tasks.length === 0 ? (
          <p style={{ textAlign: 'center', color: 'var(--text-muted)', marginTop: '2rem' }}>No tasks found. Create one above!</p>
        ) : (
          tasks.map(task => (
            <div key={task.id} className="task-item">
              <div>
                <h3>{task.title}</h3>
                {task.description && <p>{task.description}</p>}
              </div>
              <button 
                className="btn" 
                style={{ width: 'auto', background: 'var(--error-color)' }}
                onClick={() => deleteTask(task.id)}
              >
                Delete
              </button>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
