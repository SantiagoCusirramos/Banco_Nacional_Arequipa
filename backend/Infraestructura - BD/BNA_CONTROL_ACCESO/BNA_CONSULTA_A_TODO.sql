SELECT 
    u.id_usuario,
    u.nombre, -- Cambia 'nombre' por el nombre real de la columna en tu tabla usuario (ej. nombre_usuario, username, etc.)
    r.nombre_rol AS rol,
    r.descripcion AS comite_o_descripcion,
    GROUP_CONCAT(p.nombre_permiso ORDER BY p.id_permiso SEPARATOR ', ') AS permisos_asignados
FROM usuario u
INNER JOIN rol r ON u.id_rol = r.id_rol
LEFT JOIN rol_permiso rp ON r.id_rol = rp.id_rol
LEFT JOIN permiso p ON rp.id_permiso = p.id_permiso
GROUP BY u.id_usuario, r.nombre_rol, r.descripcion
ORDER BY u.id_usuario ASC;