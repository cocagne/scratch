#ifndef ABIDOS_MODEL_H
#define ABIDOS_MODEL_H



namespace abidos
{

   
class AbidosModel
{
  public:
   AbidosModel( ) {}
   
   virtual ~AbidosModel() {}

   virtual void tick() = 0;
};

   

} // end namespace abidos


#endif
