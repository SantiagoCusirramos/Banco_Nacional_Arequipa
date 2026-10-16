USE control_acceso;

SELECT 
    u.id_usuario,
    CONCAT(u.nombre, ' ', u.apellido) AS lider,
    u.correo,
    c.nombre_comite AS comite,
    r.nombre_rol AS rol
FROM usuario u
INNER JOIN comite c ON u.id_comite = c.id_comite
INNER JOIN rol r ON u.id_rol = r.id_rol
ORDER BY u.id_usuario ASC;