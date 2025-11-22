{{ fullname | escape | underline }}
===================================

.. currentmodule:: {{ module }}

.. automodule:: {{ fullname }}
   :noindex:

.. autosummary::
   :toctree:
   :nosignatures:

   {% for item in functions %}
   {{ item }}
   {% endfor %}

   {% for item in classes %}
   {{ item }}
   {% endfor %}

.. automodule:: {{ fullname }}
   :members:
   :undoc-members:
   :show-inheritance:
   :member-order: alphabetical