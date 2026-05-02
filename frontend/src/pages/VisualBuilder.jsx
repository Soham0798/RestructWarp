import { useState, useCallback, useRef, useEffect } from 'react';
import {
    DndContext,
    DragOverlay,
    useSensor,
    useSensors,
    PointerSensor,
    useDroppable,
    useDraggable,
} from '@dnd-kit/core';
import {
    LayoutGrid, Type, Image, Square, MousePointer2,
    Minus, PanelTop, FormInput, Sparkles, Trash2,
    Grid3X3, Move, Settings, GripVertical, X, PanelRightOpen, PanelRightClose
} from 'lucide-react';
import './VisualBuilder.css';

// ─── Component Registry ──────────────────────────────────────────────────────

const COMPONENT_TYPES = [
    {
        id: 'button', name: 'Button', icon: Square,
        desc: 'CTA button', color: '#954cff', bg: 'rgba(149,76,255,0.12)',
        defaultWidth: 140, defaultHeight: 44,
        defaultProps: { label: 'Click me' }
    },
    {
        id: 'text', name: 'Text Block', icon: Type,
        desc: 'Paragraph text', color: '#c084fc', bg: 'rgba(192,132,252,0.12)',
        defaultWidth: 260, defaultHeight: 60,
        defaultProps: { text: 'Lorem ipsum dolor sit amet, consectetur adipiscing elit.' }
    },
    {
        id: 'heading', name: 'Heading', icon: Type,
        desc: 'Section heading', color: '#e879f9', bg: 'rgba(232,121,249,0.12)',
        defaultWidth: 300, defaultHeight: 44,
        defaultProps: { text: 'Section Title' }
    },
    {
        id: 'image', name: 'Image', icon: Image,
        desc: 'Image placeholder', color: '#6366f1', bg: 'rgba(99,102,241,0.12)',
        defaultWidth: 240, defaultHeight: 160,
        defaultProps: { alt: 'Placeholder Image' }
    },
    {
        id: 'input', name: 'Input Field', icon: FormInput,
        desc: 'Text input', color: '#8b5cf6', bg: 'rgba(139,92,246,0.12)',
        defaultWidth: 260, defaultHeight: 44,
        defaultProps: { placeholder: 'Enter text...' }
    },
    {
        id: 'card', name: 'Card', icon: Square,
        desc: 'Content card', color: '#a78bfa', bg: 'rgba(167,139,250,0.12)',
        defaultWidth: 280, defaultHeight: 160,
        defaultProps: { title: 'Card Title', description: 'Card description goes here with more details.' }
    },
    {
        id: 'divider', name: 'Divider', icon: Minus,
        desc: 'Horizontal line', color: '#64748b', bg: 'rgba(100,116,139,0.12)',
        defaultWidth: 300, defaultHeight: 20,
        defaultProps: {}
    },
    {
        id: 'hero', name: 'Hero Section', icon: PanelTop,
        desc: 'Hero banner', color: '#ec4899', bg: 'rgba(236,72,153,0.12)',
        defaultWidth: 400, defaultHeight: 200,
        defaultProps: { title: 'Build Something Amazing', subtitle: 'Start creating today', btnText: 'Get Started' }
    },
    {
        id: 'navbar', name: 'Navbar', icon: PanelTop,
        desc: 'Navigation bar', color: '#f59e0b', bg: 'rgba(245,158,11,0.12)',
        defaultWidth: 500, defaultHeight: 50,
        defaultProps: { brand: 'MyApp', links: ['Home', 'About', 'Contact'] }
    },
];

// ─── Snap to grid helper ─────────────────────────────────────────────────────

const GRID_SIZE = 20;

function snapToGrid(x, y) {
    return [Math.round(x / GRID_SIZE) * GRID_SIZE, Math.round(y / GRID_SIZE) * GRID_SIZE];
}

// ─── Inline Editable Text ────────────────────────────────────────────────────

function InlineEditable({ value, onChange, className, style }) {
    const editRef = useRef(null);

    useEffect(() => {
        if (editRef.current) {
            editRef.current.focus();
            // Place cursor at end
            const range = document.createRange();
            range.selectNodeContents(editRef.current);
            range.collapse(false);
            const sel = window.getSelection();
            sel.removeAllRanges();
            sel.addRange(range);
        }
    }, []);

    const handleBlur = () => {
        if (editRef.current) {
            onChange(editRef.current.innerText);
        }
    };

    const handleKeyDown = (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            editRef.current?.blur();
        }
        e.stopPropagation();
    };

    return (
        <div
            ref={editRef}
            contentEditable
            suppressContentEditableWarning
            className={className}
            style={{
                ...style, outline: 'none', cursor: 'text', pointerEvents: 'auto',
                border: '1px solid var(--border-hi)', borderRadius: 4, padding: '2px 4px',
                background: 'rgba(149,76,255,0.06)', minWidth: 20, minHeight: '1em'
            }}
            onBlur={handleBlur}
            onKeyDown={handleKeyDown}
            onPointerDown={(e) => e.stopPropagation()}
        >
            {value}
        </div>
    );
}

// ─── Component Previews ──────────────────────────────────────────────────────

function ComponentPreview({ type, props, isEditing, onTextChange, onImageClick }) {
    switch (type) {
        case 'button':
            return <div className="comp-preview"><div className="comp-preview-button">{props.label}</div></div>;
        case 'text':
            return (
                <div className="comp-preview">
                    {isEditing ? (
                        <InlineEditable
                            value={props.text}
                            onChange={(val) => onTextChange?.('text', val)}
                            className="comp-preview-text"
                        />
                    ) : (
                        <div className="comp-preview-text">{props.text}</div>
                    )}
                </div>
            );
        case 'heading':
            return (
                <div className="comp-preview">
                    {isEditing ? (
                        <InlineEditable
                            value={props.text}
                            onChange={(val) => onTextChange?.('text', val)}
                            className="comp-preview-heading"
                        />
                    ) : (
                        <div className="comp-preview-heading">{props.text}</div>
                    )}
                </div>
            );
        case 'image':
            return (
                <div className="comp-preview" onClick={(e) => { e.stopPropagation(); onImageClick?.(); }}
                    style={{ cursor: 'pointer', pointerEvents: 'auto' }}>
                    {props.src ? (
                        <img src={props.src} alt={props.alt} style={{
                            width: '100%', height: '100%', objectFit: 'cover',
                            borderRadius: 8, minHeight: 80
                        }} />
                    ) : (
                        <div className="comp-preview-image">
                            <Image size={16} /> Click to upload image
                        </div>
                    )}
                </div>
            );
        case 'input':
            return <div className="comp-preview"><div className="comp-preview-input">{props.placeholder}</div></div>;
        case 'card':
            return (
                <div className="comp-preview" style={{ padding: 0 }}>
                    <div className="comp-preview-card">
                        {isEditing ? (
                            <>
                                <InlineEditable
                                    value={props.title}
                                    onChange={(val) => onTextChange?.('title', val)}
                                    className="comp-preview-card-title"
                                />
                                <InlineEditable
                                    value={props.description}
                                    onChange={(val) => onTextChange?.('description', val)}
                                    className="comp-preview-card-desc"
                                />
                            </>
                        ) : (
                            <>
                                <div className="comp-preview-card-title">{props.title}</div>
                                <div className="comp-preview-card-desc">{props.description}</div>
                            </>
                        )}
                    </div>
                </div>
            );
        case 'divider':
            return <div className="comp-preview"><div className="comp-preview-divider" /></div>;
        case 'hero':
            return (
                <div className="comp-preview" style={{ padding: 0 }}>
                    <div className="comp-preview-hero">
                        {isEditing ? (
                            <>
                                <InlineEditable
                                    value={props.title}
                                    onChange={(val) => onTextChange?.('title', val)}
                                    className="comp-preview-hero-title"
                                    style={{ WebkitTextFillColor: 'var(--p2)' }}
                                />
                                <InlineEditable
                                    value={props.subtitle}
                                    onChange={(val) => onTextChange?.('subtitle', val)}
                                    className="comp-preview-hero-sub"
                                />
                                <InlineEditable
                                    value={props.btnText}
                                    onChange={(val) => onTextChange?.('btnText', val)}
                                    className="comp-preview-hero-btn"
                                />
                            </>
                        ) : (
                            <>
                                <div className="comp-preview-hero-title">{props.title}</div>
                                <div className="comp-preview-hero-sub">{props.subtitle}</div>
                                <div className="comp-preview-hero-btn">{props.btnText}</div>
                            </>
                        )}
                    </div>
                </div>
            );
        case 'navbar':
            return (
                <div className="comp-preview" style={{ padding: 0 }}>
                    <div className="comp-preview-nav">
                        {isEditing ? (
                            <InlineEditable
                                value={props.brand}
                                onChange={(val) => onTextChange?.('brand', val)}
                                className="comp-preview-nav-brand"
                            />
                        ) : (
                            <div className="comp-preview-nav-brand">{props.brand}</div>
                        )}
                        <div className="comp-preview-nav-links">
                            {(props.links || []).map((l, i) => <span key={i} className="comp-preview-nav-link">{l}</span>)}
                        </div>
                    </div>
                </div>
            );
        default:
            return <div className="comp-preview" style={{ color: 'var(--muted)', fontSize: 12 }}>{type}</div>;
    }
}

// ─── Palette Draggable Item ──────────────────────────────────────────────────

function PaletteItem({ compType }) {
    const { attributes, listeners, setNodeRef, isDragging } = useDraggable({
        id: `palette-${compType.id}`,
        data: { fromPalette: true, componentType: compType },
    });

    const Icon = compType.icon;

    return (
        <div
            ref={setNodeRef}
            {...listeners}
            {...attributes}
            className="palette-item"
            style={{ opacity: isDragging ? 0.4 : 1 }}
        >
            <div className="palette-item-icon" style={{ background: compType.bg }}>
                <Icon size={16} color={compType.color} />
            </div>
            <div className="palette-item-info">
                <div className="palette-item-name">{compType.name}</div>
                <div className="palette-item-desc">{compType.desc}</div>
            </div>
            <GripVertical size={14} className="palette-item-drag-hint" />
        </div>
    );
}

// ─── Canvas Draggable Component ──────────────────────────────────────────────

function CanvasComponent({ component, isSelected, onSelect, onDelete, isEditing, onStartEdit, onUpdateProp, onImageUpload }) {
    const fileInputRef = useRef(null);
    // Disable drag when editing inline
    const { attributes, listeners, setNodeRef, isDragging } = useDraggable({
        id: component.id,
        data: { fromCanvas: true, component },
        disabled: isEditing,
    });

    const typeDef = COMPONENT_TYPES.find(t => t.id === component.type);
    const isEditableType = ['text', 'heading', 'hero', 'card', 'navbar'].includes(component.type);
    const isImageType = component.type === 'image';

    const handleDoubleClick = (e) => {
        e.stopPropagation();
        if (isEditableType) {
            onStartEdit?.(component.id);
        }
    };

    const handleImageClick = () => {
        fileInputRef.current?.click();
    };

    const handleFileChange = (e) => {
        const file = e.target.files?.[0];
        if (!file) return;
        const reader = new FileReader();
        reader.onload = (ev) => {
            onImageUpload?.(component.id, ev.target.result, file.name);
        };
        reader.readAsDataURL(file);
        // Reset so the same file can be re-selected
        e.target.value = '';
    };

    return (
        <div
            ref={setNodeRef}
            {...(isEditing ? {} : listeners)}
            {...attributes}
            className={`canvas-component ${isSelected ? 'selected' : ''} ${isDragging ? 'dragging' : ''} ${isEditing ? 'editing' : ''}`}
            style={{
                left: component.x,
                top: component.y,
                width: component.width,
                minHeight: component.height,
            }}
            onClick={(e) => { e.stopPropagation(); onSelect(component.id); }}
            onDoubleClick={handleDoubleClick}
        >
            <div className="canvas-component-label">
                {typeDef?.name || component.type}
                {isEditableType && !isEditing && <span style={{ marginLeft: 6, opacity: 0.5, fontSize: 8 }}>double-click to edit</span>}
                {isImageType && <span style={{ marginLeft: 6, opacity: 0.5, fontSize: 8 }}>click to upload</span>}
            </div>
            <button
                className="canvas-component-delete"
                onClick={(e) => { e.stopPropagation(); onDelete(component.id); }}
                onPointerDown={(e) => e.stopPropagation()}
            >
                <X size={10} color="#fff" />
            </button>
            {isImageType && (
                <input
                    ref={fileInputRef}
                    type="file"
                    accept="image/*"
                    style={{ display: 'none' }}
                    onChange={handleFileChange}
                />
            )}
            <ComponentPreview
                type={component.type}
                props={component.props}
                isEditing={isEditing}
                onTextChange={(key, val) => onUpdateProp?.(component.id, key, val)}
                onImageClick={isImageType ? handleImageClick : undefined}
            />
        </div>
    );
}

// ─── Canvas Drop Zone ────────────────────────────────────────────────────────

function CanvasDropZone({ children, isOver }) {
    const { setNodeRef } = useDroppable({ id: 'canvas' });

    return (
        <div
            ref={setNodeRef}
            className={`canvas-drop-zone ${isOver ? 'drag-over' : ''}`}
        >
            {children}
        </div>
    );
}

// ─── Properties Panel ────────────────────────────────────────────────────────

function PropertiesPanel({ component, onUpdate }) {
    if (!component) {
        return (
            <div className="builder-properties">
                <div className="properties-header">
                    <div className="properties-title"><Settings size={15} /> Properties</div>
                </div>
                <div className="properties-content">
                    <div className="properties-empty">
                        <MousePointer2 size={28} />
                        <div className="properties-empty-text">Select a component to view its properties</div>
                    </div>
                </div>
            </div>
        );
    }

    const typeDef = COMPONENT_TYPES.find(t => t.id === component.type);

    const handlePropChange = (key, value) => {
        onUpdate(component.id, {
            ...component,
            props: { ...component.props, [key]: value }
        });
    };

    const handlePosChange = (key, value) => {
        const num = parseInt(value, 10);
        if (!isNaN(num)) {
            onUpdate(component.id, { ...component, [key]: snapToGrid(num, num)[0] });
        }
    };

    return (
        <div className="builder-properties">
            <div className="properties-header">
                <div className="properties-title"><Settings size={15} /> Properties</div>
            </div>
            <div className="properties-content">
                {/* Type info */}
                <div className="prop-group">
                    <div className="prop-label">Component</div>
                    <div style={{
                        display: 'flex', alignItems: 'center', gap: 8, padding: '8px 12px',
                        borderRadius: 8, background: typeDef?.bg || 'rgba(255,255,255,0.04)',
                        border: '1px solid var(--border)', fontSize: 12, fontWeight: 600, color: 'var(--text)'
                    }}>
                        {typeDef && <typeDef.icon size={14} color={typeDef.color} />}
                        {typeDef?.name || component.type}
                    </div>
                </div>

                {/* Position */}
                <div className="prop-group">
                    <div className="prop-label">Position</div>
                    <div className="prop-position">
                        <div className="prop-position-item">
                            <span className="prop-position-label">X</span>
                            <input className="prop-input" type="number" value={component.x}
                                onChange={e => handlePosChange('x', e.target.value)} step={GRID_SIZE} />
                        </div>
                        <div className="prop-position-item">
                            <span className="prop-position-label">Y</span>
                            <input className="prop-input" type="number" value={component.y}
                                onChange={e => handlePosChange('y', e.target.value)} step={GRID_SIZE} />
                        </div>
                    </div>
                </div>

                {/* Size */}
                <div className="prop-group">
                    <div className="prop-label">Size</div>
                    <div className="prop-position">
                        <div className="prop-position-item">
                            <span className="prop-position-label">W</span>
                            <input className="prop-input" type="number" value={component.width}
                                onChange={e => handlePosChange('width', e.target.value)} step={GRID_SIZE} />
                        </div>
                        <div className="prop-position-item">
                            <span className="prop-position-label">H</span>
                            <input className="prop-input" type="number" value={component.height}
                                onChange={e => handlePosChange('height', e.target.value)} step={GRID_SIZE} />
                        </div>
                    </div>
                </div>

                {/* Dynamic props */}
                {Object.entries(component.props).map(([key, value]) => {
                    if (Array.isArray(value)) return null; // skip arrays for now
                    return (
                        <div className="prop-group" key={key}>
                            <div className="prop-label">{key}</div>
                            <input className="prop-input" type="text" value={value}
                                onChange={e => handlePropChange(key, e.target.value)} />
                        </div>
                    );
                })}
            </div>
        </div>
    );
}

// ─── Main Visual Builder ─────────────────────────────────────────────────────

let nextId = 1;
function genId() { return `comp-${nextId++}-${Date.now()}`; }

const VisualBuilder = () => {
    const [components, setComponents] = useState([]);
    const [selectedId, setSelectedId] = useState(null);
    const [editingId, setEditingId] = useState(null);
    const [activeItem, setActiveItem] = useState(null);
    const [isOver, setIsOver] = useState(false);
    const [showProperties, setShowProperties] = useState(false);
    const canvasRef = useRef(null);

    const sensors = useSensors(
        useSensor(PointerSensor, { activationConstraint: { distance: 5 } })
    );

    const selectedComponent = components.find(c => c.id === selectedId) || null;

    // Delete on key press
    useEffect(() => {
        const onKey = (e) => {
            if ((e.key === 'Delete' || e.key === 'Backspace') && selectedId) {
                // Don't delete if user is typing in an input or editing inline
                if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA' || e.target.isContentEditable || editingId) return;
                setComponents(prev => prev.filter(c => c.id !== selectedId));
                setSelectedId(null);
            }
            if (e.key === 'Escape') {
                if (editingId) {
                    setEditingId(null);
                } else {
                    setSelectedId(null);
                }
            }
        };
        window.addEventListener('keydown', onKey);
        return () => window.removeEventListener('keydown', onKey);
    }, [selectedId, editingId]);

    const handleDragStart = useCallback((event) => {
        setActiveItem(event.active);
    }, []);

    const handleDragOver = useCallback((event) => {
        setIsOver(!!event.over);
    }, []);

    const handleDragEnd = useCallback((event) => {
        setActiveItem(null);
        setIsOver(false);

        const { active, over, delta } = event;
        if (!over || over.id !== 'canvas') return;

        const data = active.data.current;

        // Drag from palette — create new component
        if (data?.fromPalette) {
            const compType = data.componentType;
            // Calculate drop position relative to canvas
            const canvasEl = canvasRef.current;
            if (!canvasEl) return;
            const canvasRect = canvasEl.getBoundingClientRect();

            // Use the activatorEvent position + delta
            const pointerX = (event.activatorEvent?.clientX || 0) + delta.x - canvasRect.left + canvasEl.scrollLeft;
            const pointerY = (event.activatorEvent?.clientY || 0) + delta.y - canvasRect.top + canvasEl.scrollTop;

            const [snappedX, snappedY] = snapToGrid(
                Math.max(0, pointerX - compType.defaultWidth / 2),
                Math.max(0, pointerY - compType.defaultHeight / 2)
            );

            const newComp = {
                id: genId(),
                type: compType.id,
                x: snappedX,
                y: snappedY,
                width: compType.defaultWidth,
                height: compType.defaultHeight,
                props: { ...compType.defaultProps },
            };

            setComponents(prev => [...prev, newComp]);
            setSelectedId(newComp.id);
        }

        // Drag on canvas — move existing component
        if (data?.fromCanvas) {
            const comp = data.component;
            const [snappedX, snappedY] = snapToGrid(
                comp.x + delta.x,
                comp.y + delta.y
            );
            setComponents(prev =>
                prev.map(c => c.id === comp.id ? { ...c, x: Math.max(0, snappedX), y: Math.max(0, snappedY) } : c)
            );
        }
    }, []);

    const handleDragCancel = useCallback(() => {
        setActiveItem(null);
        setIsOver(false);
    }, []);

    const handleDeleteComponent = useCallback((id) => {
        setComponents(prev => prev.filter(c => c.id !== id));
        if (selectedId === id) setSelectedId(null);
    }, [selectedId]);

    const handleUpdateComponent = useCallback((id, updated) => {
        setComponents(prev => prev.map(c => c.id === id ? updated : c));
    }, []);

    // Inline text edit: update a single prop key (keeps editing mode for multi-field components)
    const handleUpdateProp = useCallback((id, key, value) => {
        setComponents(prev => prev.map(c =>
            c.id === id ? { ...c, props: { ...c.props, [key]: value } } : c
        ));
    }, []);

    // Image upload: set src and alt on the component
    const handleImageUpload = useCallback((id, dataUrl, fileName) => {
        setComponents(prev => prev.map(c =>
            c.id === id ? { ...c, props: { ...c.props, src: dataUrl, alt: fileName } } : c
        ));
    }, []);

    const handleClearAll = useCallback(() => {
        setComponents([]);
        setSelectedId(null);
        setEditingId(null);
    }, []);

    // Build drag overlay content
    let overlayContent = null;
    if (activeItem) {
        const data = activeItem.data.current;
        if (data?.fromPalette) {
            const compType = data.componentType;
            const Icon = compType.icon;
            overlayContent = (
                <div className="drag-overlay-item">
                    <div className="palette-item-icon" style={{ background: compType.bg }}>
                        <Icon size={14} color={compType.color} />
                    </div>
                    {compType.name}
                </div>
            );
        }
        if (data?.fromCanvas) {
            const comp = data.component;
            overlayContent = (
                <div style={{
                    width: comp.width, minHeight: comp.height,
                    background: 'rgba(14,12,26,0.9)', border: '1px solid var(--border-hi)',
                    borderRadius: 8, boxShadow: '0 8px 32px rgba(0,0,0,0.5), 0 0 24px rgba(149,76,255,0.2)',
                    opacity: 0.9
                }}>
                    <ComponentPreview type={comp.type} props={comp.props} />
                </div>
            );
        }
    }

    return (
        <DndContext
            sensors={sensors}
            onDragStart={handleDragStart}
            onDragOver={handleDragOver}
            onDragEnd={handleDragEnd}
            onDragCancel={handleDragCancel}
        >
            <div className="builder-page">
                {/* ── Palette ── */}
                <div className="builder-palette">
                    <div className="palette-header">
                        <div className="palette-title"><LayoutGrid size={16} /> Components</div>
                        <div className="palette-subtitle">Drag onto canvas</div>
                    </div>
                    <div className="palette-items">
                        <div className="palette-section-label">UI Elements</div>
                        {COMPONENT_TYPES.filter(t => ['button', 'text', 'heading', 'input', 'divider'].includes(t.id)).map(ct => (
                            <PaletteItem key={ct.id} compType={ct} />
                        ))}
                        <div className="palette-section-label">Blocks</div>
                        {COMPONENT_TYPES.filter(t => ['image', 'card', 'hero', 'navbar'].includes(t.id)).map(ct => (
                            <PaletteItem key={ct.id} compType={ct} />
                        ))}
                    </div>
                </div>

                {/* ── Canvas Area ── */}
                <div className="builder-canvas-area">
                    <div className="canvas-toolbar">
                        <div className="canvas-toolbar-left">
                            <div className="canvas-info-pill">
                                <Grid3X3 size={12} />
                                {GRID_SIZE}px grid
                            </div>
                            <div className="canvas-info-pill">
                                <Sparkles size={12} />
                                {components.length} component{components.length !== 1 ? 's' : ''}
                            </div>
                        </div>
                        <div className="canvas-toolbar-right">
                            {components.length > 0 && (
                                <button className="toolbar-btn danger" onClick={handleClearAll}>
                                    <Trash2 size={12} /> Clear All
                                </button>
                            )}
                            <button className="toolbar-btn" onClick={() => setShowProperties(p => !p)}>
                                {showProperties ? <PanelRightClose size={12} /> : <PanelRightOpen size={12} />}
                                {showProperties ? 'Hide Props' : 'Properties'}
                            </button>
                        </div>
                    </div>

                    <div className="canvas-container" ref={canvasRef} onClick={() => setSelectedId(null)}>
                        <CanvasDropZone isOver={isOver}>
                            {components.length === 0 && !activeItem && (
                                <div className="canvas-empty">
                                    <div className="canvas-empty-icon">
                                        <Move size={24} color="var(--p2)" />
                                    </div>
                                    <div className="canvas-empty-text">Drop components here</div>
                                    <div className="canvas-empty-hint">Drag items from the palette on the left</div>
                                </div>
                            )}
                            {components.map(comp => (
                                <CanvasComponent
                                    key={comp.id}
                                    component={comp}
                                    isSelected={selectedId === comp.id}
                                    isEditing={editingId === comp.id}
                                    onSelect={setSelectedId}
                                    onDelete={handleDeleteComponent}
                                    onStartEdit={setEditingId}
                                    onUpdateProp={handleUpdateProp}
                                    onImageUpload={handleImageUpload}
                                />
                            ))}
                        </CanvasDropZone>
                    </div>
                </div>

                {/* ── Properties Panel ── */}
                {showProperties && (
                    <PropertiesPanel
                        component={selectedComponent}
                        onUpdate={handleUpdateComponent}
                    />
                )}
            </div>

            {/* ── Drag Overlay ── */}
            <DragOverlay dropAnimation={null}>
                {overlayContent}
            </DragOverlay>
        </DndContext>
    );
};

export default VisualBuilder;
